"""Query helpers shared by panel views, search providers and the dashboard."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db.models import Q, QuerySet, Sum
from django.utils import timezone

from apps.core.cache import safe_cache_get, safe_cache_set
from apps.core.jalali_forms import parse_jalali_safe
from apps.core.text import normalize_fa
from apps.orders.models import PAID_STATES, Order

SALES_TTL = 60  # D44: dashboard numbers may be cached for at most 60 s


def order_search_q(raw: str) -> Q | None:
    """Number, tracking code, names, or (part of) a mobile number; Persian digits are fine."""
    text = normalize_fa(raw)[:40].strip()
    if not text:
        return None
    condition = (
        Q(number__icontains=text)
        | Q(tracking_code__icontains=text)
        | Q(buyer_name__icontains=text)
        | Q(recipient_name__icontains=text)
    )
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        condition |= Q(buyer_mobile__contains=digits) | Q(recipient_mobile__contains=digits)
    return condition


def day_range(raw_from: str | None, raw_to: str | None):
    """Jalali days -> [low, high) aware datetimes in Tehran. The end day is included; a reversed range is swapped."""
    start, end = parse_jalali_safe(raw_from), parse_jalali_safe(raw_to)
    if start and end and start > end:
        start, end = end, start
    low = timezone.make_aware(datetime.combine(start, time.min)) if start else None
    high = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min)) if end else None
    return low, high


def within(queryset: QuerySet, field: str, low, high) -> QuerySet:
    if low is not None:
        queryset = queryset.filter(**{f"{field}__gte": low})
    if high is not None:
        queryset = queryset.filter(**{f"{field}__lt": high})
    return queryset


def orders_to_ship() -> int:
    return Order.objects.filter(status__in=(Order.PAID, Order.PROCESSING)).count()


def sales_last_30_days() -> int:
    cached = safe_cache_get("panel:sales30")
    if isinstance(cached, int):
        return cached
    since = timezone.now() - timedelta(days=30)
    total = Order.objects.filter(status__in=PAID_STATES, paid_at__gte=since).aggregate(t=Sum("payable"))["t"] or 0
    safe_cache_set("panel:sales30", total, SALES_TTL)
    return total


def ship_queue(user) -> dict:
    rows = list(Order.objects.filter(status__in=(Order.PAID, Order.PROCESSING)).order_by("paid_at", "pk")[:5])
    return {"queue": rows, "can_manage": user.has_perm("orders.manage_order_status")}
