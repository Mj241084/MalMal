"""Business rules of the home page and collections (P5)."""

from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalog.models import Category, Product, Variant
from apps.core.jalali_admin import EndOfDayJalaliDateTimeField
from apps.core.jalali_forms import JalaliDateTimeField
from apps.marketing.models import Banner, Collection, CollectionItem, HomeBlock
from apps.marketing.services import collection_products, home_context


def _banner(alt, **kwargs):
    return Banner.objects.create(
        title=alt, alt=alt, image_desktop="banners/x.webp", placement=Banner.PLACEMENT_HERO, **kwargs
    )


def _hero_alts(now=None):
    return [b["alt"] for block in home_context(now)["home_blocks"] for b in block.get("banners", [])]


def _block(**kwargs):
    """Replace the blocks seeded by the data migration with the one this test needs."""
    HomeBlock.objects.all().delete()
    return HomeBlock.objects.create(**kwargs)


def _make(title, category, price, compare=None, stock=3):
    item = Product.objects.create(title=title, category=category, status=Product.STATUS_ACTIVE)
    Variant.objects.create(product=item, sku=title, title="x", price=price, compare_at_price=compare, stock=stock)
    return item


@pytest.mark.parametrize(
    "fields",
    [
        {"target_type": "product"},  # type without a target
        {"target_type": "none", "target_url": "/c/1/x/"},  # a target the type does not use
        {"target_type": "url", "target_url": "javascript:alert(1)"},
        {"target_type": "url", "target_url": "//evil.example"},
    ],
)
def test_banner_target_must_match_its_type(fields):
    with pytest.raises(ValidationError):
        Banner(title="t", alt="a", image_desktop="banners/x.webp", **fields).clean()


@pytest.mark.django_db
def test_banners_appear_and_disappear_on_time_without_invalidation():
    now = timezone.now()
    _block(kind=HomeBlock.HERO, sort=1)
    _banner("live", starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1))
    _banner("expired", ends_at=now - timedelta(minutes=1))
    _banner("future", starts_at=now + timedelta(minutes=1))

    assert _hero_alts(now) == ["live"]
    assert _hero_alts(now + timedelta(days=2)) == ["future"]  # same cached data, later clock


@pytest.mark.django_db
def test_banner_with_a_dead_target_is_hidden(product, django_capture_on_commit_callbacks):
    _block(kind=HomeBlock.HERO, sort=1)
    _banner("linked", target_type=Banner.TARGET_PRODUCT, target_product=product)
    assert _hero_alts() == ["linked"]

    with django_capture_on_commit_callbacks(execute=True):
        product.status = Product.STATUS_DRAFT
        product.save()
    assert _hero_alts() == []


@pytest.mark.django_db
def test_editing_a_banner_refreshes_the_home_page(django_capture_on_commit_callbacks):
    _block(kind=HomeBlock.HERO, sort=1)
    banner = _banner("old")
    assert _hero_alts() == ["old"]

    with django_capture_on_commit_callbacks(execute=True):
        banner.alt = "new"
        banner.save()
    assert _hero_alts() == ["new"]


@pytest.mark.django_db
def test_best_selling_rail_needs_real_purchases(product):
    _block(kind=HomeBlock.PRODUCT_RAIL, rail_source=HomeBlock.SOURCE_BEST, sort=1)

    def rails():
        return [b for b in home_context()["home_blocks"] if b["kind"] == "rail"]

    assert rails() == []
    Product.objects.filter(pk=product.pk).update(purchase_count_30d=3)
    cache.clear()
    assert len(rails()) == 1


@pytest.mark.django_db
def test_rule_collection_filters_by_subtree_discount_and_stock(root_category, child_category, product):
    other_root = Category.objects.create(name="دیگر")
    _make("plain", child_category, 100)  # in the subtree, no discount
    _make("outside", other_root, 100, 200)  # discounted, other tree
    _make("soldout", child_category, 100, 200, stock=0)  # discounted, no stock
    collection = Collection.objects.create(title="c", mode=Collection.MODE_RULE, min_discount_pct=5, only_in_stock=True)
    collection.categories.add(root_category)

    queryset, _ = collection_products(collection)

    assert set(queryset.values_list("pk", flat=True)) == {product.pk}


@pytest.mark.django_db
def test_manual_collection_keeps_the_editors_order(product, child_category):
    second = _make("second", child_category, 100)
    collection = Collection.objects.create(title="m", mode=Collection.MODE_MANUAL)
    CollectionItem.objects.create(collection=collection, product=second, sort=1)
    CollectionItem.objects.create(collection=collection, product=product, sort=2)

    queryset, ordering = collection_products(collection)

    assert [p.pk for p in queryset.order_by(*ordering)] == [second.pk, product.pk]


@pytest.mark.django_db
def test_collection_page_respects_active_flag_and_window(client):
    now = timezone.now()
    live = Collection.objects.create(title="a", slug="a")
    expired = Collection.objects.create(title="b", slug="b", ends_at=now - timedelta(hours=1))
    inactive = Collection.objects.create(title="c", slug="c", is_active=False)

    assert client.get(live.get_absolute_url()).status_code == 200
    assert client.get(expired.get_absolute_url()).status_code == 404
    assert client.get(inactive.get_absolute_url()).status_code == 404


def test_end_date_without_time_means_end_of_day_in_tehran():
    start = JalaliDateTimeField().to_python("۱۴۰۵/۰۶/۳۰")
    end = EndOfDayJalaliDateTimeField().to_python("۱۴۰۵/۰۶/۳۰")
    explicit = EndOfDayJalaliDateTimeField().to_python("۱۴۰۵/۰۶/۳۰ ۱۰:۰۰")

    assert start.astimezone(UTC) == datetime(2026, 9, 20, 20, 30, tzinfo=UTC)
    assert end.astimezone(UTC) == datetime(2026, 9, 21, 20, 29, tzinfo=UTC)
    assert explicit.hour == 10
