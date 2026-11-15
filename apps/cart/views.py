"""Cart views: page, guest render, add/set/sync for the signed-in cart (docs/02 §5)."""

from __future__ import annotations

import json

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django_htmx.http import trigger_client_event

from apps.cart import services
from apps.core.decorators import login_required_htmx
from apps.orders.shipping import default_method


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _context(lines, notices, *, guest: bool) -> dict:
    return {
        "lines": lines,
        "notices": notices,
        "summary": services.summarize(lines),
        "method": default_method(),
        "guest": guest,
        "normalized": json.dumps([{"v": line.variant.pk, "q": line.qty} for line in lines]),
    }


def _announce(response, count: int, message: str = "", ok: bool = True):
    trigger_client_event(response, "cart:changed", {"count": count, "message": message, "ok": ok})
    return response


@require_GET
def detail_view(request):
    if request.user.is_authenticated:
        lines, notices = services.normalize(services.get_cart(request.user))
        context = _context(lines, notices, guest=False)
    else:
        context = {"guest": True}
    return render(request, "pages/cart.html", context)


@require_POST
def render_view(request):
    """Guest cart: price/stock/limits for the localStorage items. Nothing is written."""
    lines = services.resolve_lines(services.parse_items(request.POST.get("items")))
    response = render(request, "partials/_cart_content.html", _context(lines, services.notices_for(lines), guest=True))
    return _announce(response, len(lines))


@login_required_htmx
@require_POST
def add_view(request):
    try:
        message, ok = services.add_one(request.user, _int(request.POST.get("variant_id"))), True
    except services.CartError as exc:
        message, ok = str(exc), False
    return _announce(HttpResponse(status=204), services.count(request.user), message, ok)


@login_required_htmx
@require_POST
def set_view(request):
    try:
        message, ok = (
            services.set_quantity(request.user, _int(request.POST.get("variant_id")), _int(request.POST.get("qty"))),
            True,
        )
    except services.CartError as exc:
        message, ok = str(exc), False
    lines, notices = services.normalize(services.get_cart(request.user))
    response = render(request, "partials/_cart_content.html", _context(lines, notices, guest=False))
    return _announce(response, len(lines), message, ok)


@login_required_htmx
@require_POST
def sync_view(request):
    services.merge_guest_items(request.user, services.parse_items(request.POST.get("items")))
    return _announce(HttpResponse(status=204), services.count(request.user))
