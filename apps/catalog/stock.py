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
