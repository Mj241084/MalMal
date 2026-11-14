"""Materialized-path subtree queries (docs/03 §4, phase P1 DoD)."""

from __future__ import annotations

import pytest

from apps.catalog.models import Category, Product
from apps.catalog.tree import subtree_upper_bound


def _make_product(category: Category, title: str) -> Product:
    return Product.objects.create(
        title=title,
        category=category,
        status=Product.STATUS_ACTIVE,
    )


@pytest.mark.django_db
def test_paths_are_materialized():
    root = Category.objects.create(name="ریشه")
    child = Category.objects.create(name="فرزند", parent=root)
    grandchild = Category.objects.create(name="نوه", parent=child)

    assert root.path == f"{root.pk}/"
    assert child.path == f"{root.pk}/{child.pk}/"
    assert grandchild.path == f"{root.pk}/{child.pk}/{grandchild.pk}/"
    assert (root.depth, child.depth, grandchild.depth) == (0, 1, 2)


@pytest.mark.django_db
def test_subtree_range_excludes_similar_prefix():
    """``1/5/`` must not swallow ``1/50/`` (the whole point of the range query)."""
    root = Category.objects.create(pk=1, name="ریشه")
    five = Category.objects.create(pk=5, name="پنج", parent=root)
    fifty = Category.objects.create(pk=50, name="پنجاه", parent=root)
    deep = Category.objects.create(name="عمیق", parent=five)

    assert five.path == "1/5/"
    assert fifty.path == "1/50/"
    assert subtree_upper_bound(five.path) == "1/50"

    _make_product(five, "محصول پنج")
    _make_product(deep, "محصول عمیق")
    _make_product(fifty, "محصول پنجاه")

    from apps.catalog.views import _subtree_products

    titles = set(_subtree_products(five).values_list("title", flat=True))
    assert titles == {"محصول پنج", "محصول عمیق"}

    root_titles = set(_subtree_products(root).values_list("title", flat=True))
    assert root_titles == {"محصول پنج", "محصول عمیق", "محصول پنجاه"}


@pytest.mark.django_db
def test_moving_category_rewrites_descendant_paths_and_products():
    first = Category.objects.create(name="اول")
    second = Category.objects.create(name="دوم")
    branch = Category.objects.create(name="شاخه", parent=first)
    leaf = Category.objects.create(name="برگ", parent=branch)
    product = _make_product(leaf, "محصول برگ")

    old_leaf_path = leaf.path
    branch.parent = second
    branch.save()

    leaf.refresh_from_db()
    product.refresh_from_db()
    assert leaf.path == f"{second.path}{branch.pk}/{leaf.pk}/"
    assert leaf.path != old_leaf_path
    assert product.category_path == leaf.path

    from apps.catalog.views import _subtree_products

    assert list(_subtree_products(second).values_list("pk", flat=True)) == [product.pk]
    assert not _subtree_products(first).exists()


@pytest.mark.django_db
def test_category_change_bumps_subtree_rev_of_ancestors(django_capture_on_commit_callbacks):
    root = Category.objects.create(name="ریشه")
    child = Category.objects.create(name="فرزند", parent=root)
    before = Category.objects.get(pk=root.pk).subtree_rev

    with django_capture_on_commit_callbacks(execute=True):
        child.name = "فرزند تغییرکرده"
        child.save()

    assert Category.objects.get(pk=root.pk).subtree_rev == before + 1
