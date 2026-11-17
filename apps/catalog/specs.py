"""Which specification attributes apply to a category (D41)."""

from __future__ import annotations

from decimal import Decimal

from apps.catalog.models import SpecAttribute


def applicable_attributes(category):
    """The category's own attributes plus its ancestors', as far up as each `spec_inherit` allows. Root first."""
    ids = [category.pk]
    node = category
    for parent in reversed(category.ancestors()):  # nearest parent first
        if not node.spec_inherit:
            break
        ids.append(parent.pk)
        node = parent
    return (
        SpecAttribute.objects.filter(category_id__in=ids)
        .select_related("category")
        .order_by("category__depth", "sort", "pk")
    )


def number_text(number: Decimal) -> str:
    """ASCII text of a number spec for `value_text` (facets read it): 9.50 -> '9.5', 100.00 -> '100'."""
    return format(number.normalize(), "f")
