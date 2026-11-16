"""Cart views: page, guest render, add/set/line/sync/state for the signed-in cart (docs/02 §5)."""

from __future__ import annotations

import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django_htmx.http import trigger_client_event

from apps.cart import services
from apps.core.decorators import login_required_htmx
from apps.engagement import social
from apps.orders.shipping import default_method

MAX_STATE_IDS = 30


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _context(lines, notices, *, guest: bool, user=None) -> dict:
    return {
        "lines": lines,
        "notices": notices,
        "summary": services.summarize(lines),
        "method": default_method(),
        "guest": guest,
        "normalized": json.dumps([{"v": line.variant.pk, "q": line.qty} for line in lines]),
        "social": social.cart_notes(lines, user),
    }


def _announce(response, count: int, message: str = "", ok: bool = True, line: tuple[int, int] | None = None):
    detail = {"count": count, "message": message, "ok": ok}
    if line is not None:  # the product page learns the real stored quantity from this
        detail["variant"], detail["qty"] = line
    trigger_client_event(response, "cart:changed", detail)
    return response


def _line_announce(request, variant_id: int, message: str, ok: bool):
    qty = services.quantity(request.user, variant_id)
    return _announce(HttpResponse(status=204), services.count(request.user), message, ok, line=(variant_id, qty))


@require_GET
def detail_view(request):
    if request.user.is_authenticated:
        lines, notices = services.normalize(services.get_cart(request.user))
        context = _context(lines, notices, guest=False, user=request.user)
    else:
        context = {"guest": True}
    return render(request, "pages/cart.html", context)


@require_POST
def render_view(request):
    """Guest cart: price/stock/limits for the localStorage items. Nothing is written."""
    lines = services.resolve_lines(services.parse_items(request.POST.get("items")))
    response = render(request, "partials/_cart_content.html", _context(lines, services.notices_for(lines), guest=True))
    return _announce(response, len(lines))


@require_GET
def state_view(request):
    """Quantities of the given variants in the signed-in viewer's cart (product page stepper)."""
    ids: list[int] = []
    for part in (request.GET.get("variants") or "").split(","):
        part = part.strip()
        if part.isascii() and part.isdigit() and len(part) <= 12 and int(part) not in ids:
            ids.append(int(part))
        if len(ids) == MAX_STATE_IDS:
            break
    quantities = {str(pk): qty for pk, qty in services.quantities(request.user, ids).items()}
    response = JsonResponse({"qty": quantities})
    response["Cache-Control"] = "private, no-store"
    return response


@login_required_htmx
@require_POST
def add_view(request):
    variant_id = _int(request.POST.get("variant_id"))
    try:
        message, ok = services.add_one(request.user, variant_id), True
    except services.CartError as exc:
        message, ok = str(exc), False
    return _line_announce(request, variant_id, message, ok)


@login_required_htmx
@require_POST
def line_view(request):
    """Absolute quantity of one line, answered with 204 + event (no cart render): the product page stepper."""
    variant_id = _int(request.POST.get("variant_id"))
    try:
        message, ok = services.set_quantity(request.user, variant_id, _int(request.POST.get("qty"))), True
    except services.CartError as exc:
        message, ok = str(exc), False
    return _line_announce(request, variant_id, message, ok)


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
    response = render(request, "partials/_cart_content.html", _context(lines, notices, guest=False, user=request.user))
    return _announce(response, len(lines), message, ok)


@login_required_htmx
@require_POST
def sync_view(request):
    services.merge_guest_items(request.user, services.parse_items(request.POST.get("items")))
    return _announce(HttpResponse(status=204), services.count(request.user))
