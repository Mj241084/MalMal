"""Social-proof text (docs/02 §9): only real numbers, nothing under the thresholds."""

from __future__ import annotations

from decimal import Decimal

from apps.core.jalali import to_fa_digits
from apps.engagement.models import Like

LIKE_MIN = 5
PURCHASE_MIN = 5
DECIMAL_SEP = "٫"


def compact_count(n: int) -> str:
    """۹۹۹ → «۹۹۹»، ۱۲۰۰ → «۱٫۲ هزار». Truncated, never rounded up: the number must stay true."""
    if n >= 1_000_000:
        tenths, unit = n // 100_000, " میلیون"
    elif n >= 1_000:
        tenths, unit = n // 100, " هزار"
    else:
        return to_fa_digits(n)
    whole, fraction = divmod(tenths, 10)
    number = f"{whole}{DECIMAL_SEP}{fraction}" if fraction else str(whole)
    return to_fa_digits(number) + unit


def product_lines(product, *, liked: bool) -> list[str]:
    """Like and purchase lines for one product. `liked` is the viewer's own state."""
    lines: list[str] = []
    likes = max(product.like_count, 1) if liked else product.like_count  # a stale counter never shows «شما و ۰ نفر»
    if liked:
        if likes == 1:
            lines.append("شما این محصول را پسندیده‌اید")
        else:
            lines.append(f"شما و {compact_count(likes - 1)} نفر دیگر این محصول را پسندیده‌اید")
    elif likes >= LIKE_MIN:
        lines.append(f"{compact_count(likes)} نفر این محصول را پسندیده‌اند")
    if product.purchase_count_30d >= PURCHASE_MIN:
        lines.append(f"{compact_count(product.purchase_count_30d)} نفر در ۳۰ روز گذشته این محصول را خریده‌اند")
    return lines


def low_stock_line(variant, threshold: int) -> str:
    if 0 < variant.stock <= threshold:
        return f"تنها {to_fa_digits(variant.stock)} عدد در انبار باقی مانده"
    return ""


def rating_summary(product) -> dict | None:
    if not product.review_count:
        return None
    average = Decimal(product.rating_avg)
    return {
        "text": to_fa_digits(f"{average:.1f}").replace(".", DECIMAL_SEP),
        "stars": int(average + Decimal("0.5")),
        "count": compact_count(product.review_count),
    }


def cart_notes(lines, user) -> dict[int, list[str]]:
    """Per-variant social and low-stock lines for the cart page. One query for the viewer's likes."""
    from apps.core.models import SiteSettings

    available = [line for line in lines if line.available]
    liked_ids: set[int] = set()
    if user is not None and user.is_authenticated and available:
        liked_ids = set(
            Like.objects.filter(user=user, product_id__in={line.variant.product_id for line in available}).values_list(
                "product_id", flat=True
            )
        )
    threshold = SiteSettings.get_solo().low_stock_threshold
    notes: dict[int, list[str]] = {}
    for line in available:
        product = line.variant.product
        stock_line = low_stock_line(line.variant, threshold)
        notes[line.variant.pk] = [
            *product_lines(product, liked=product.pk in liked_ids),
            *([stock_line] if stock_line else []),
        ]
    return notes
