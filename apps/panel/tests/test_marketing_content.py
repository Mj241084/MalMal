"""Marketing and content through the panel: hidden targets, inclusive end day, epoch, ordering, footer safety."""

import io
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.catalog.cache import current_epoch
from apps.catalog.models import Product
from apps.core.jalali import to_fa_digits
from apps.core.models import FooterLink, StaticPage
from apps.core.templatetags.core_tags import _icon_exists
from apps.marketing.models import Banner, Collection, CollectionItem, HomeBlock, TrustItem
from apps.marketing.services import collection_products
from apps.panel.forms_marketing import TRUST_ICONS

pytestmark = pytest.mark.django_db


def _png(name="banner.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def test_banner_save_drops_the_hidden_target_and_ends_at_the_end_of_the_day(staff_client, settings, tmp_path, product):
    settings.MEDIA_ROOT = tmp_path
    client = staff_client("marketing.view_banner", "marketing.add_banner")

    response = client.post(
        reverse("panel:banner_new"),
        {
            "title": "تست", "placement": Banner.PLACEMENT_HERO, "is_active": "on", "image_desktop": _png(),
            "alt": "متن", "target_type": Banner.TARGET_URL, "target_product": str(product.pk),
            "target_url": "/pages/terms/", "starts_at": "", "ends_at": "۱۴۰۵/۰۶/۳۰",
        },
    )  # fmt: skip

    assert response.status_code == 302
    banner = Banner.objects.get(title="تست")
    assert banner.target_product is None and banner.target_url == "/pages/terms/"
    ends = timezone.localtime(banner.ends_at)
    assert (ends.date(), ends.hour, ends.minute) == (date(2026, 9, 21), 23, 59)


def test_toggling_a_banner_moves_the_home_epoch(staff_client, django_capture_on_commit_callbacks):
    banner = Banner.objects.create(title="x", alt="x", image_desktop="banners/x.png")
    client = staff_client("marketing.view_banner", "marketing.change_banner")
    before = current_epoch()

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("panel:banner_action", args=[banner.pk, "toggle"]))

    banner.refresh_from_db()
    assert banner.is_active is False and current_epoch() > before


def test_a_second_hero_is_refused_with_a_form_error(staff_client):
    if not HomeBlock.objects.filter(kind=HomeBlock.HERO).exists():
        HomeBlock.objects.create(kind=HomeBlock.HERO)
    client = staff_client("marketing.view_homeblock", "marketing.add_homeblock")

    response = client.post(
        reverse("panel:block_new"), {"kind": HomeBlock.HERO, "title": "", "limit": "12", "is_active": "on"}
    )

    assert response.status_code == 200
    assert HomeBlock.objects.filter(kind=HomeBlock.HERO).count() == 1


def test_the_live_rule_count_matches_the_collection_it_would_save(staff_client, product):
    collection = Collection.objects.create(
        title="قاعده", mode=Collection.MODE_RULE, min_discount_pct=5, only_in_stock=True
    )
    expected = collection_products(collection)[0].count()

    response = staff_client("marketing.view_collection").get(
        reverse("panel:collection_preview"), {"min_discount_pct": "5", "only_in_stock": "on"}
    )

    assert expected == 1
    assert to_fa_digits(f"{expected} محصول") in response.content.decode()


def test_reordering_swaps_neighbours_even_for_rows_without_updated_at(staff_client, product):
    TrustItem.objects.all().delete()
    first = TrustItem.objects.create(icon="truck", title="الف", sort=0)
    second = TrustItem.objects.create(icon="lock", title="ب", sort=1)
    other = Product.objects.create(title="دوم", category=product.category, status=Product.STATUS_ACTIVE)
    collection = Collection.objects.create(title="ترتیب")
    one = CollectionItem.objects.create(collection=collection, product=product, sort=0)
    two = CollectionItem.objects.create(collection=collection, product=other, sort=1)
    client = staff_client(
        "marketing.view_trustitem", "marketing.change_trustitem", "marketing.view_collection",
        "marketing.change_collectionitem",
    )  # fmt: skip

    client.post(reverse("panel:trust_action", args=[second.pk, "up"]))
    client.post(reverse("panel:collection_item_action", args=[collection.pk, two.pk, "up"]))

    assert [TrustItem.objects.get(pk=i.pk).sort for i in (first, second)] == [1, 0]
    assert [CollectionItem.objects.get(pk=i.pk).sort for i in (one, two)] == [1, 0]


def test_footer_urls_are_checked_and_a_linked_page_cannot_be_deleted(staff_client):
    page = StaticPage.objects.get_or_create(slug="terms", defaults={"title": "قوانین"})[0]
    client = staff_client(
        "core.view_footerlink", "core.add_footerlink", "core.view_staticpage", "core.delete_staticpage"
    )
    bad = {"group": FooterLink.GROUP_ABOUT, "title": "بد", "url": "javascript:alert(1)", "is_active": "on"}
    good = {"group": FooterLink.GROUP_ABOUT, "title": "خوب", "page": str(page.pk), "url": "", "is_active": "on"}

    assert client.post(reverse("panel:link_new"), bad).status_code == 200
    assert not FooterLink.objects.filter(title="بد").exists()
    assert client.post(reverse("panel:link_new"), good).status_code == 302
    assert FooterLink.objects.get(title="خوب").url == "/pages/terms/"

    client.post(reverse("panel:page_delete", args=[page.pk]))
    assert StaticPage.objects.filter(pk=page.pk).exists()


def test_writes_need_their_own_permission(staff_client):
    assert staff_client("marketing.view_banner").get(reverse("panel:banner_new")).status_code == 403


@pytest.mark.django_db(False)
def test_every_trust_icon_exists_in_the_built_sprite():
    missing = [name for name in TRUST_ICONS if not _icon_exists(name)]
    assert not missing, missing
