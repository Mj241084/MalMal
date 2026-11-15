import pytest

from apps.catalog.cache import similar_key
from apps.catalog.models import Category, Product, Variant
from apps.catalog.similar import base_category, similar_products

pytestmark = pytest.mark.django_db


def _make(title, category, *, sku, brand=None, price=46_800_000, stock=3, status=Product.STATUS_ACTIVE, **extra):
    item = Product.objects.create(title=title, category=category, brand=brand, status=status, **extra)
    Variant.objects.create(product=item, sku=sku, title="سفید", price=price, stock=stock)
    item.refresh_from_db()
    return item


def test_candidates_exclude_self_drafts_and_sold_out(product, child_category):
    mate = _make("هم‌دسته", child_category, sku="A")
    _make("پیش‌نویس", child_category, sku="B", status=Product.STATUS_DRAFT)
    _make("ناموجود", child_category, sku="C", stock=0)

    assert [p.pk for p in similar_products(product)] == [mate.pk]


def test_same_leaf_beats_same_brand_in_a_sibling_category(product, brand, child_category, root_category):
    other_leaf = Category.objects.create(name="یخچال", parent=root_category)
    sibling = _make("هم‌برند", other_leaf, sku="S", brand=brand, purchase_count_30d=50)
    mate = _make("هم‌دسته", child_category, sku="L")

    assert [p.pk for p in similar_products(product)] == [mate.pk, sibling.pk]


def test_cache_key_moves_when_a_candidate_is_added(product, child_category, django_capture_on_commit_callbacks):
    def key() -> str:
        fresh = Product.objects.select_related("category__parent").get(pk=product.pk)
        return similar_key(fresh, base_category(fresh))

    before = key()
    with django_capture_on_commit_callbacks(execute=True):
        _make("تازه", child_category, sku="NEW")

    assert key() != before
