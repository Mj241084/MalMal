"""Atomic stock changes (CLAUDE.md §4). Callers must already be inside transaction.atomic()."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.db.models import F

from apps.catalog import cache as catalog_cache
from apps.catalog.constants import LEVEL_DETAIL
from apps.catalog.models import Product, StockMovement, Variant
from apps.core.models import SiteSettings


class InsufficientStock(Exception):
    def __init__(self, variant_id: int):
        super().__init__(f"Not enough stock for variant {variant_id}")
        self.variant_id = variant_id


class StockConflict(Exception):
    """A manual change was refused: stock would go below zero, or it is no longer what the staff member saw."""

    def __init__(self, variant_id: int, current: int | None):
        super().__init__(f"Stock of variant {variant_id} is {current}")
        self.variant_id = variant_id
        self.current = current


def _invalidate_if_visible(variant_id: int, delta: int) -> None:
    """The cached product page shows 'sold out', 'only N left' and the per-order cap: bump it when a move touches that zone."""
    row = Variant.objects.filter(pk=variant_id).values_list("stock", "max_per_order", "product_id").first()
    if row is None:
        return
    stock_now, cap, product_id = row
    zone = max(SiteSettings.get_solo().low_stock_threshold, cap or 0)
    if min(stock_now - delta, stock_now) <= zone:
        transaction.on_commit(lambda: catalog_cache.touch_product(product_id, LEVEL_DETAIL), robust=True)


def decrement(variant_id: int, qty: int, *, reason: str, order_item_id: int | None = None, note: str = "") -> None:
    updated = Variant.objects.filter(pk=variant_id, is_active=True, stock__gte=qty).update(stock=F("stock") - qty)
    if updated != 1:
        raise InsufficientStock(variant_id)
    StockMovement.objects.create(
        variant_id=variant_id, delta=-qty, reason=reason, order_item_id=order_item_id, note=note
    )
    _invalidate_if_visible(variant_id, -qty)


def increment(variant_id: int, qty: int, *, reason: str, order_item_id: int | None = None, note: str = "") -> None:
    Variant.objects.filter(pk=variant_id).update(stock=F("stock") + qty)
    StockMovement.objects.create(
        variant_id=variant_id, delta=qty, reason=reason, order_item_id=order_item_id, note=note
    )
    _invalidate_if_visible(variant_id, qty)


def refresh_products(product_ids: Iterable[int]) -> None:
    """Recompute aggregates after stock moves; cache rev only bumps when in_stock flips (docs/03 §5)."""
    for product in Product.objects.filter(pk__in=set(product_ids)):
        product.refresh_aggregates()


def adjust_manual(variant_id: int, delta: int, *, note: str, expected_stock: int | None = None) -> int:
    """Staff stock change (D43): atomic compare-and-set, ledger row, aggregates, cache. Returns the new stock.

    Callers are inside transaction.atomic(). This path never goes through Variant.save(), so it does the
    aggregates, the cache bump and the «back in stock» marking itself.
    """
    if not delta:
        raise ValueError("delta must not be zero")
    rows = Variant.objects.filter(pk=variant_id, stock__gte=-delta)
    if expected_stock is not None:
        rows = rows.filter(stock=expected_stock)
    if not rows.update(stock=F("stock") + delta):
        current = Variant.objects.filter(pk=variant_id).values_list("stock", flat=True).first()
        raise StockConflict(variant_id, current)
    new_stock, active, product_id = (
        Variant.objects.filter(pk=variant_id).values_list("stock", "is_active", "product_id").get()
    )
    StockMovement.objects.create(
        variant_id=variant_id, delta=delta, reason=StockMovement.REASON_MANUAL, note=note[:255]
    )
    _invalidate_if_visible(variant_id, delta)
    refresh_products([product_id])
    if new_stock - delta == 0 and new_stock > 0 and active:  # a real restock: stock leaves zero
        from apps.engagement import back_in_stock

        transaction.on_commit(lambda: back_in_stock.mark_due(variant_id), robust=True)
    return new_stock
