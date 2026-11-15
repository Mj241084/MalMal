"""Atomic stock changes (CLAUDE.md §4). Callers must already be inside transaction.atomic()."""

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import F

from apps.catalog.models import Product, StockMovement, Variant


class InsufficientStock(Exception):
    def __init__(self, variant_id: int):
        super().__init__(f"Not enough stock for variant {variant_id}")
        self.variant_id = variant_id


def decrement(variant_id: int, qty: int, *, reason: str, order_item_id: int | None = None, note: str = "") -> None:
    updated = Variant.objects.filter(pk=variant_id, is_active=True, stock__gte=qty).update(stock=F("stock") - qty)
    if updated != 1:
        raise InsufficientStock(variant_id)
    StockMovement.objects.create(
        variant_id=variant_id, delta=-qty, reason=reason, order_item_id=order_item_id, note=note
    )


def increment(variant_id: int, qty: int, *, reason: str, order_item_id: int | None = None, note: str = "") -> None:
    Variant.objects.filter(pk=variant_id).update(stock=F("stock") + qty)
    StockMovement.objects.create(
        variant_id=variant_id, delta=qty, reason=reason, order_item_id=order_item_id, note=note
    )


def refresh_products(product_ids: Iterable[int]) -> None:
    """Recompute aggregates after stock moves; cache rev only bumps when in_stock flips (docs/03 §5)."""
    for product in Product.objects.filter(pk__in=set(product_ids)):
        product.refresh_aggregates()
