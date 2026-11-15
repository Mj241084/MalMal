"""COUNTER writes (docs/03 §5): F() and aggregate updates that never invalidate caches.

With stock.py, the only place allowed to call `.update()` on Product outside models (architecture test).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, F, IntegerField, Sum, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from apps.catalog.models import Product
from apps.engagement.models import Like, ProductDailyStat, Review

WINDOW_DAYS = 30
STAT_RETENTION_DAYS = 90


def average(total: int, count: int) -> Decimal:
    if not count:
        return Decimal("0.0")
    return (Decimal(total) / count).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def add_likes(product_id: int, delta: int) -> None:
    Product.objects.filter(pk=product_id).update(
        like_count=Greatest(F("like_count") + delta, Value(0), output_field=IntegerField())
    )


def add_purchases(qty_by_product: dict[int, int]) -> None:
    """Total + rolling counters and today's ledger row. Callers are inside transaction.atomic() (IMMEDIATE)."""
    today = timezone.localdate()
    for product_id, qty in qty_by_product.items():
        Product.objects.filter(pk=product_id).update(
            purchase_count_total=F("purchase_count_total") + qty,
            purchase_count_30d=F("purchase_count_30d") + qty,
        )
        today_row = ProductDailyStat.objects.filter(product_id=product_id, date=today)
        if not today_row.update(purchases=F("purchases") + qty):
            ProductDailyStat.objects.create(product_id=product_id, date=today, purchases=qty)


def reconcile(product_ids: Iterable[int] | None = None) -> int:
    """Recompute like and approved-review counters from the source rows. Idempotent; returns products fixed."""
    ids = None if product_ids is None else list(product_ids)
    products, likes_qs, reviews_qs = (
        Product.objects.all(),
        Like.objects.all(),
        Review.objects.filter(status=Review.APPROVED),
    )
    if ids is not None:
        products = products.filter(pk__in=ids)
        likes_qs = likes_qs.filter(product_id__in=ids)
        reviews_qs = reviews_qs.filter(product_id__in=ids)

    likes = dict(likes_qs.values("product_id").annotate(n=Count("pk")).order_by().values_list("product_id", "n"))
    reviews = {
        row["product_id"]: (row["n"], row["total"])
        for row in reviews_qs.values("product_id").annotate(n=Count("pk"), total=Sum("rating")).order_by()
    }

    fixed = 0
    rows = list(products.values_list("pk", "like_count", "review_count", "rating_sum", "rating_avg"))
    for pk, like_count, review_count, rating_sum, rating_avg in rows:
        n, total = reviews.get(pk, (0, 0))
        wanted = (likes.get(pk, 0), n, total, average(total, n))
        if (like_count, review_count, rating_sum, rating_avg) != wanted:
            Product.objects.filter(pk=pk).update(
                like_count=wanted[0], review_count=wanted[1], rating_sum=wanted[2], rating_avg=wanted[3]
            )
            fixed += 1
    return fixed


def recount_purchases(today: date | None = None) -> int:
    """Rolling 30-day window from the daily ledger; also trims ledger rows older than 90 days."""
    today = today or timezone.localdate()
    since = today - timedelta(days=WINDOW_DAYS - 1)
    sums = dict(
        ProductDailyStat.objects.filter(date__gte=since)
        .values("product_id")
        .annotate(total=Sum("purchases"))
        .order_by()
        .values_list("product_id", "total")
    )
    fixed = 0
    for pk, current in list(Product.objects.values_list("pk", "purchase_count_30d")):
        wanted = sums.get(pk, 0)
        if current != wanted:
            Product.objects.filter(pk=pk).update(purchase_count_30d=wanted)
            fixed += 1
    ProductDailyStat.objects.filter(date__lt=today - timedelta(days=STAT_RETENTION_DAYS)).delete()
    return fixed
