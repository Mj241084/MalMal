from __future__ import annotations

from django import template

from apps.panel import badges, nav
from apps.payments.models import Payment

register = template.Library()

PAYMENT_DOT = {Payment.VERIFIED: "status-success", Payment.VERIFYING: "status-info", Payment.FAILED: "status-error"}


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
