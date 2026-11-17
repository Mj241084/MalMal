from __future__ import annotations

from django import template
from django.conf import settings

from apps.core.jalali import to_fa_digits
from apps.panel import badges, nav, queries
from apps.payments.models import Payment

register = template.Library()

PAYMENT_DOT = {Payment.VERIFIED: "status-success", Payment.VERIFYING: "status-info", Payment.FAILED: "status-error"}
REVIEW_DOT = {"pending": "status-warning", "approved": "status-success", "rejected": "status-error"}
PRODUCT_DOT = {"active": "status-success", "draft": "status-warning", "archived": "status-neutral"}


@register.inclusion_tag("panel/partials/sidebar.html", takes_context=True)
def render_sidebar(context, oob=False):
    request = context["request"]
    return {
        "groups": nav.visible_groups(request.user, request.path),
        "counts": badges.counts_for(request.user),
        "request": request,
        "oob": oob,
    }


@register.inclusion_tag("panel/partials/badge.html")
def render_badge(key: str, counts: dict[str, int]):
    count = counts.get(key, 0)
    return {"key": key, "count": count, "visible": count > 0}


@register.filter
def payment_dot(status: str) -> str:
    return PAYMENT_DOT.get(status, "status-neutral")


@register.filter
def review_dot(status: str) -> str:
    return REVIEW_DOT.get(status, "status-neutral")


@register.filter
def product_dot(status: str) -> str:
    return PRODUCT_DOT.get(status, "status-neutral")


@register.filter
def stamp(moment) -> int:
    return queries.stamp(moment)


@register.filter
def signed(value) -> str:
    number = int(value)
    return to_fa_digits(f"+{number}" if number > 0 else str(number))


@register.filter
def thumb_url(image) -> str:
    """Smallest rendition of a ProductImage, for table rows and cards."""
    if not image:
        return ""
    if image.widths:
        return f"{settings.MEDIA_URL}{image.widths[min(image.widths, key=int)]}"
    return image.image.url if image.image else ""
