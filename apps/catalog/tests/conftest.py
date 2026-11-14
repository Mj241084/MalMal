"""Factories for catalog tests."""

from __future__ import annotations

import pytest

from apps.catalog.models import Brand, Category, Product, Variant


@pytest.fixture
def brand(db):
    return Brand.objects.create(name_fa="بوش", name_en="Bosch", aliases="بوش، Bosch")


@pytest.fixture
def root_category(db):
    return Category.objects.create(name="لوازم خانگی")


@pytest.fixture
def child_category(db, root_category):
    return Category.objects.create(name="ماشین لباسشویی", parent=root_category)


@pytest.fixture
def product(db, brand, child_category):
    item = Product.objects.create(
        title="ماشین لباسشویی بوش مدل WM-1234",
        brand=brand,
        category=child_category,
        status=Product.STATUS_ACTIVE,
        short_description="لباسشویی ۹ کیلویی",
    )
    Variant.objects.create(
        product=item,
        sku="WM-1234",
        title="سفید",
        price=46_800_000,
        compare_at_price=52_000_000,
        stock=5,
    )
    item.refresh_from_db()
    return item
