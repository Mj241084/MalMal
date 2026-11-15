"""Per-order quantity cap (D29) and DB-driven trust items (P1 fixes)."""

from __future__ import annotations

import pytest
from django import forms

from apps.catalog.models import Product, Variant
from apps.marketing.models import TrustItem
from apps.orders.models import ShippingMethod

VariantForm = forms.modelform_factory(Variant, fields=["title", "sku", "price", "stock", "max_per_order"])


def _variant(stock: int, cap: int | None) -> Variant:
    return Variant(stock=stock, max_per_order=cap, price=1000, sku="SKU-X", title="x")


@pytest.mark.parametrize(
    ("stock", "cap", "expected"),
    [
        (10, None, 10),  # empty cap -> whole stock
        (10, 0, 10),  # zero cap -> whole stock
        (10, 2, 2),  # cap below stock wins
        (3, 10, 3),  # cap above stock -> stock wins
        (0, 5, 0),  # no stock means nothing orderable
        (0, None, 0),
    ],
)
def test_max_orderable(stock, cap, expected):
    assert _variant(stock, cap).max_orderable == expected


@pytest.mark.django_db
def test_variant_form_accepts_empty_and_zero_cap(product):
    for value in ("", 0, 2):
        form = VariantForm(data={"title": "سفید", "sku": "SKU-FORM", "price": 1000, "stock": 5, "max_per_order": value})
        assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_variant_form_rejects_negative_cap(product):
    form = VariantForm(data={"title": "سفید", "sku": "SKU-NEG", "price": 1000, "stock": 5, "max_per_order": -1})
    assert not form.is_valid()
    assert "max_per_order" in form.errors


@pytest.mark.django_db
def test_changing_cap_invalidates_product_detail_cache(product, django_capture_on_commit_callbacks):
    variant = product.variants.first()
    before = Product.objects.get(pk=product.pk).rev

    with django_capture_on_commit_callbacks(execute=True):
        variant.max_per_order = 2
        variant.save()

    assert Product.objects.get(pk=product.pk).rev == before + 1


@pytest.mark.django_db
def test_product_page_shows_cap_only_when_below_stock(client, product, django_capture_on_commit_callbacks):
    variant = product.variants.first()
    variant.stock = 10
    with django_capture_on_commit_callbacks(execute=True):
        variant.save()

    assert "حداکثر" not in client.get(product.get_absolute_url()).content.decode()

    variant.max_per_order = 2
    with django_capture_on_commit_callbacks(execute=True):
        variant.save()

    body = client.get(product.get_absolute_url()).content.decode()
    assert "حداکثر ۲ عدد در هر سفارش" in body


@pytest.mark.django_db
def test_editing_trust_item_refreshes_product_page(client, product, django_capture_on_commit_callbacks):
    item = TrustItem.objects.create(icon="truck", title="متن قدیمی", sort=0)
    assert "متن قدیمی" in client.get(product.get_absolute_url()).content.decode()

    with django_capture_on_commit_callbacks(execute=True):
        item.title = "متن تازه"
        item.save()

    body = client.get(product.get_absolute_url()).content.decode()
    assert "متن تازه" in body
    assert "متن قدیمی" not in body


@pytest.mark.django_db
def test_shipping_note_comes_from_the_active_method_with_settings_as_fallback(
    client, product, django_capture_on_commit_callbacks
):
    from apps.core.models import SiteSettings

    ShippingMethod.objects.all().delete()
    with django_capture_on_commit_callbacks(execute=True):
        method = ShippingMethod.objects.create(code="t1", title="تیپاکس", product_note="کرایه با گیرنده")
    assert "کرایه با گیرنده" in client.get(product.get_absolute_url()).content.decode()

    with django_capture_on_commit_callbacks(execute=True):
        method.delete()
        site = SiteSettings.get_solo()
        site.shipping_note = "ارسال آزمایشی با پیک"
        site.save()
    body = client.get(product.get_absolute_url()).content.decode()
    assert "ارسال آزمایشی با پیک" in body and "کرایه با گیرنده" not in body
