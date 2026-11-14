"""FTS5 search: normalization, index maintenance, and fallback (docs/03 §7)."""

from __future__ import annotations

import pytest
from django.db import connection

from apps.catalog.models import Brand, Category, Product, Variant
from apps.search.index import rebuild_all, search_product_ids


def _ids(query: str) -> set[int]:
    return set(search_product_ids(query, limit=50))


@pytest.fixture
def catalog(db):
    samsung = Brand.objects.create(name_fa="سامسونگ", name_en="Samsung", aliases="سامسونگ، Samsung")
    bosch = Brand.objects.create(name_fa="بوش", name_en="Bosch")
    category = Category.objects.create(name="لوازم خانگی")
    laundry = Category.objects.create(name="ماشین لباسشویی", parent=category)

    washer = Product.objects.create(
        title="ماشین لباسشویی بوش مدل WM-1234",
        brand=bosch,
        category=laundry,
        status=Product.STATUS_ACTIVE,
    )
    Variant.objects.create(product=washer, sku="WM-1234", title="سفید", price=10, stock=1)

    fridge = Product.objects.create(
        title="یخچال سامسونگ ۱۲۳ لیتری",
        brand=samsung,
        category=laundry,
        status=Product.STATUS_ACTIVE,
    )
    Variant.objects.create(product=fridge, sku="RF-123", title="نقره‌ای", price=20, stock=1)

    vacuum = Product.objects.create(
        title="جاروبرقی فیلیپس",
        category=laundry,
        status=Product.STATUS_ACTIVE,
    )
    Variant.objects.create(product=vacuum, sku="FC-9174", title="مشکی", price=30, stock=1)

    rebuild_all()
    return {"washer": washer, "fridge": fridge, "vacuum": vacuum}


@pytest.mark.django_db
def test_kashida_and_arabic_letters_are_normalized(catalog):
    washer = catalog["washer"]
    assert washer.pk in _ids("WM-1234")

    # Arabic yeh/kaf and tatweel must resolve to the same product set.
    assert _ids("يخچال") == _ids("یخچال")
    assert _ids("ماشين") == _ids("ماشین")
    assert _ids("ماشيـن") == _ids("ماشین")


@pytest.mark.django_db
def test_kashida_inside_word_matches(catalog):
    category = Category.objects.create(name="دیجیتال")
    phone = Product.objects.create(title="موبایل سامسونگ", category=category, status=Product.STATUS_ACTIVE)
    Variant.objects.create(product=phone, sku="MB-1", title="مشکی", price=100, stock=1)
    rebuild_all()

    assert phone.pk in _ids("موبایل")
    assert phone.pk in _ids("موبایـل")
    assert _ids("موبایل") == _ids("موبایـل")


@pytest.mark.django_db
def test_persian_and_ascii_digits_match(catalog):
    fridge = catalog["fridge"]
    assert fridge.pk in _ids("۱۲۳")
    assert fridge.pk in _ids("123")
    assert _ids("۱۲۳") == _ids("123")


@pytest.mark.django_db
def test_model_code_with_and_without_hyphen(catalog):
    washer = catalog["washer"]
    assert washer.pk in _ids("WM-1234")
    assert washer.pk in _ids("WM1234")
    assert _ids("WM-1234") == _ids("WM1234")


@pytest.mark.django_db
def test_brand_alias_matches(catalog):
    fridge = catalog["fridge"]
    assert fridge.pk in _ids("Samsung")
    assert fridge.pk in _ids("samsung")


@pytest.mark.django_db
def test_prefix_on_last_term(catalog):
    assert catalog["washer"].pk in _ids("لباسش")


@pytest.mark.django_db
def test_fallback_to_like_when_fts_finds_nothing(catalog):
    """«برق» is only a substring of the token «جاروبرقی», so FTS misses it."""
    vacuum = catalog["vacuum"]
    assert vacuum.pk in _ids("برق")


@pytest.mark.django_db
def test_index_follows_edit_deactivate_and_delete(catalog, django_capture_on_commit_callbacks):
    washer = catalog["washer"]
    assert washer.pk not in _ids("ظرفشویی")

    with django_capture_on_commit_callbacks(execute=True):
        washer.title = "ماشین ظرفشویی بوش"
        washer.save()
    assert washer.pk in _ids("ظرفشویی")

    with django_capture_on_commit_callbacks(execute=True):
        washer.status = Product.STATUS_DRAFT
        washer.save()
    assert washer.pk not in _ids("ظرفشویی")

    with django_capture_on_commit_callbacks(execute=True):
        washer.status = Product.STATUS_ACTIVE
        washer.save()
    assert washer.pk in _ids("ظرفشویی")

    washer_pk = washer.pk
    washer.delete()
    assert washer_pk not in _ids("ظرفشویی")


@pytest.mark.django_db
def test_index_rows_match_active_products(catalog):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM product_fts")
        assert cursor.fetchone()[0] == Product.objects.filter(status=Product.STATUS_ACTIVE).count()
