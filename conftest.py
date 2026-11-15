"""Shared test fixtures: isolated Redis cache, clean FTS index, geo data, and shop factories."""

from __future__ import annotations

import pytest
from django.core.cache import cache, caches
from django.db import connection
from django.test.testcases import DatabaseOperationForbidden

from apps.accounts.models import Address, User
from apps.cart import services as cart_services
from apps.catalog.models import Brand, Category, Product, Variant
from apps.geo.models import City, Province
from apps.orders.models import ShippingMethod
from apps.orders.services import place_order
from apps.payments.models import PaymentGateway


def _clear_fts() -> None:
    """The FTS table is not managed by Django, so rows survive table truncation."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM product_fts")
    except (DatabaseOperationForbidden, RuntimeError):
        # SimpleTestCase subclasses (and pytest-django's blocker) forbid DB access.
        return


@pytest.fixture(autouse=True)
def clean_cache_and_index():
    """Redis holds real counters and the FTS table is not managed by Django."""
    caches["ratelimit"].clear()
    cache.clear()
    _clear_fts()
    yield
    caches["ratelimit"].clear()
    cache.clear()


@pytest.fixture
def province(db) -> Province:
    return Province.objects.create(name="تهران", slug="tehran", sort=1)


@pytest.fixture
def city(db, province) -> City:
    return City.objects.create(province=province, name="تهران", slug="tehran")


@pytest.fixture
def other_province(db) -> Province:
    return Province.objects.create(name="اصفهان", slug="isfahan", sort=2)


@pytest.fixture
def other_city(db, other_province) -> City:
    return City.objects.create(province=other_province, name="اصفهان", slug="isfahan")


# --- catalog factories -----------------------------------------------------


@pytest.fixture
def brand(db) -> Brand:
    return Brand.objects.create(name_fa="بوش", name_en="Bosch", aliases="بوش، Bosch")


@pytest.fixture
def root_category(db) -> Category:
    return Category.objects.create(name="لوازم خانگی")


@pytest.fixture
def child_category(db, root_category) -> Category:
    return Category.objects.create(name="ماشین لباسشویی", parent=root_category)


@pytest.fixture
def product(db, brand, child_category) -> Product:
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


# --- checkout factories ----------------------------------------------------


@pytest.fixture
def checkout_env(db, settings):
    """Dev gateway visible, SMS on console, and the seed rows a TransactionTestCase flush may have wiped."""
    settings.DEBUG = True
    settings.SMS_BACKEND = "console"
    method, _ = ShippingMethod.objects.get_or_create(
        code="tipax",
        defaults={"title": "ارسال با تیپاکس", "checkout_note": "پس‌کرایه", "max_weight_g": 100_000},
    )
    PaymentGateway.objects.get_or_create(code="fake", defaults={"title": "درگاه آزمایشی"})
    return method


@pytest.fixture
def buyer(db) -> User:
    return User.objects.create_user("09121230001", first_name="مریم", last_name="احمدی", national_code="0012345679")


@pytest.fixture
def address(buyer, province, city) -> Address:
    return Address.objects.create(
        user=buyer,
        recipient_name="مریم احمدی",
        recipient_mobile=buyer.mobile,
        province=province,
        city=city,
        address_text="خیابان ولیعصر",
        plate="12",
        postal_code="1234567890",
        is_default=True,
    )


@pytest.fixture
def cart_item(buyer, product, checkout_env):
    variant = product.variants.get()
    cart_services.set_quantity(buyer, variant.pk, 2)
    return variant


@pytest.fixture
def placed_order(buyer, address, cart_item, checkout_env):
    lines, _ = cart_services.normalize(cart_services.get_cart(buyer))
    return place_order(
        user=buyer,
        address=address,
        method=checkout_env,
        buyer_form=None,
        seen_fingerprint=cart_services.fingerprint(lines),
    )
