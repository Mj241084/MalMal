from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Count, Q, QuerySet, Sum
from django.utils import timezone

from apps.catalog.models import Product, Variant
from apps.core.cache import safe_cache_get, safe_cache_set
from apps.core.jalali import to_fa_digits
from apps.core.jalali_forms import parse_jalali_safe
from apps.core.models import SiteSettings
from apps.core.text import normalize_fa
from apps.engagement.models import Review
from apps.notifications import sms
from apps.orders.models import PAID_STATES, Order

SALES_TTL = 60  # D44: dashboard numbers may be cached for at most 60 s


# --- Existing query helpers --------------------------------------------------


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


# --- Phase 12 helpers --------------------------------------------------------


def stamp(moment) -> int:
    """Version of a row as the moderator saw it: a decision is refused when the row changed meanwhile."""
    return int(moment.timestamp() * 1_000_000)


def reviews_pending() -> int:
    return Review.objects.filter(status=Review.PENDING).count()


def review_queue(user) -> dict:
    rows = list(Review.objects.filter(status=Review.PENDING).select_related("product").order_by("created_at", "pk")[:5])
    return {"review_queue": rows, "can_moderate": user.has_perm("engagement.change_review")}


def stock_board(product_id: int | None = None):
    """Variants the inventory page manages: sellable ones of live products, or every variant of one product."""
    if product_id:
        return Variant.objects.filter(product_id=product_id)
    return Variant.objects.filter(product__status=Product.STATUS_ACTIVE, is_active=True)


def stock_alert_count() -> int:
    return stock_board().filter(stock__lte=SiteSettings.get_solo().low_stock_threshold).count()


def wanted_out_of_stock(limit: int = 5) -> list[Variant]:
    return list(
        stock_board()
        .filter(stock__lte=0)
        .annotate(waiting=Count("stock_subscriptions", filter=Q(stock_subscriptions__notified_at__isnull=True)))
        .filter(waiting__gt=0)
        .select_related("product")
        .order_by("-waiting", "pk")[:limit]
    )


def restock_send_hint(now=None) -> str:
    """When the «back in stock» SMS of a queued restock goes out (docs/02 §13)."""
    if not sms.template_is_configured("back_in_stock"):
        return "قالب پیامک «موجود شد» تنظیم نشده است"
    site = SiteSettings.get_solo()
    if now is None:
        now = timezone.now()
    if site.back_in_stock_start_hour <= timezone.localtime(now).hour < site.back_in_stock_end_hour:
        return "در اجرای بعدی (حداکثر ۱۰ دقیقه)"
    return f"از ساعت {to_fa_digits(f'{site.back_in_stock_start_hour:02d}:00')}"


# --- Phase 14 helpers --------------------------------------------------------


def customer_search_q(raw: str) -> Q | None:
    """Name, or (part of) a mobile number or national code; Persian digits are fine."""
    text = normalize_fa(raw)[:40].strip()
    if not text:
        return None
    condition = Q(first_name__icontains=text) | Q(last_name__icontains=text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 3:
        condition |= Q(mobile__contains=digits) | Q(national_code__contains=digits)
    return condition


def backup_status() -> dict | None:
    """Newest db-*.sqlite3 in BACKUP_DIR. None when BACKUP_DIR is unset or missing; empty name when no copy exists."""
    if not settings.BACKUP_DIR:
        return None
    folder = Path(settings.BACKUP_DIR)
    if not folder.is_dir():
        return None
    files = sorted(folder.glob("db-*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        return {"name": "", "at": None, "stale": True}
    moment = datetime.fromtimestamp(files[0].stat().st_mtime, tz=timezone.get_current_timezone())
    return {"name": files[0].name, "at": moment, "stale": timezone.now() - moment > timedelta(days=2)}
