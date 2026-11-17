"""Regression tests for the Nov 2026 review fixes (data integrity, money, search cache)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.orders import services as order_services


def test_moving_a_category_keeps_product_paths_clean(db):
    # ids chosen so that the old path "1/" also occurs inside the child's path "1/11/"
    a = Category.objects.create(id=1, name="الف")
    b = Category.objects.create(id=2, name="ب")
    c = Category.objects.create(id=11, name="ج", parent=a)
    item = Product.objects.create(title="کالا", category=c)

    a.parent = b
    a.save()

    item.refresh_from_db()
    assert item.category_path == "2/1/11/"


def test_extend_reservation_refuses_an_expired_order(placed_order):
    ended = timezone.now() - timedelta(minutes=1)
    placed_order.reserved_until = ended
    placed_order.save(update_fields=["reserved_until"])

    assert order_services.extend_reservation(placed_order.pk) is False

    placed_order.refresh_from_db()
    assert placed_order.reserved_until == ended


def test_category_rename_refreshes_product_search_text(product, child_category, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        child_category.name = "ظرفشویی"
        child_category.save()

    product.refresh_from_db()
    assert "ظرفشویی" in product.search_text


def test_variant_sku_change_refreshes_product_search_text(product):
    variant = product.variants.get()
    variant.sku = "ZZ-9999"
    variant.save()

    product.refresh_from_db()
    assert "zz-9999" in product.search_text
