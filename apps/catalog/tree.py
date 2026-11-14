"""Materialized-path helpers for the category tree (docs/03-data-model.md §4).

Paths look like ``"1/5/12/"``. A subtree query uses a half-open range instead of
``startswith`` so SQLite can use the index:

    path >= "1/5/"  AND  path < "1/5/0"

The upper bound is the path with its trailing ``/`` replaced by ``"0"`` because
``"/"`` (0x2F) sorts immediately before ``"0"`` (0x30), so ``"1/50/"`` is excluded.
"""

from __future__ import annotations

from django.db.models import Value
from django.db.models.functions import Replace


def subtree_upper_bound(path: str) -> str:
    """Return the exclusive upper bound of the subtree range for ``path``."""
    return path[:-1] + "0"


def compute_path(category) -> str:
    """Build the materialized path for a category from its parent."""
    if category.parent_id:
        parent_path = category.parent.path
        return f"{parent_path}{category.pk}/"
    return f"{category.pk}/"


def depth_of(path: str) -> int:
    """Depth of a materialized path: ``"1/5/"`` -> 1."""
    return max(path.count("/") - 1, 0)


def ancestor_ids(path: str) -> list[int]:
    """Ids encoded in a materialized path, root first: ``"1/5/12/"`` -> [1, 5, 12]."""
    return [int(part) for part in path.split("/") if part]


def move_subtree(category, old_path: str) -> None:
    """Recompute paths of descendants and denormalized product paths after a move.

    Must run inside the same transaction as the category save. Raw ``update()``
    calls are allowed here only (see the architecture test).
    """
    from apps.catalog.models import Category, Product

    new_path = category.path
    if new_path == old_path:
        return

    lower = old_path
    upper = subtree_upper_bound(old_path)

    descendants = Category.objects.filter(path__gte=lower, path__lt=upper).exclude(pk=category.pk)
    for descendant in descendants:
        suffix = descendant.path[len(old_path) :]
        updated = f"{new_path}{suffix}"
        Category.objects.filter(pk=descendant.pk).update(path=updated, depth=depth_of(updated))

    Product.objects.filter(category_path__gte=lower, category_path__lt=upper).update(
        category_path=Replace("category_path", Value(old_path), Value(new_path))
    )
