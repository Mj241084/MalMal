"""Inventory in the panel: the stock board, the ledger and the one place staff change stock (docs/09 module 7)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django_htmx.http import reswap, retarget

from apps.catalog import services
from apps.catalog.models import Product, StockMovement, Variant
from apps.catalog.stock import StockConflict
from apps.core.jalali import to_fa_digits
from apps.core.models import SiteSettings
from apps.core.text import normalize_fa
from apps.orders.models import OrderItem
from apps.panel import audit, htmx, queries
from apps.panel.forms_stock import StockAdjustForm
from apps.panel.permissions import panel_view

PAGE_SIZE = 25
VIEW, LEDGER, ADJUST = "catalog.view_variant", "catalog.view_stockmovement", "catalog.adjust_stock"
STATES = (("alert", "ناموجود و کم‌موجود"), ("out", "ناموجود"), ("low", "کم‌موجود"), ("in", "موجود"))
LIST_PARAMS = ("page", "q", "state", "product")


def _digits(raw) -> int | None:
    raw = str(raw or "")
    return int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= 12 else None


def _stock_context(params, user) -> dict:
    low = SiteSettings.get_solo().low_stock_threshold
    product_id = _digits(params.get("product"))
    queryset = (
        queries.stock_board(product_id)
        .select_related("product__main_image")
        .annotate(
            waiting=Count("stock_subscriptions", filter=Q(stock_subscriptions__notified_at__isnull=True)),
            queued=Count(
                "stock_subscriptions",
                filter=Q(
                    stock_subscriptions__restocked_at__isnull=False, stock_subscriptions__notified_at__isnull=True
                ),
            ),
        )
    )
    text = normalize_fa(params.get("q", ""), for_search=True)[:60]
    if text:
        queryset = queryset.filter(Q(sku__icontains=text) | Q(product__search_text__contains=text))
    state = params.get("state", "")
    if state == "alert":
        queryset = queryset.filter(stock__lte=low)
    elif state == "out":
        queryset = queryset.filter(stock__lte=0)
    elif state == "low":
        queryset = queryset.filter(stock__gt=0, stock__lte=low)
    elif state == "in":
        queryset = queryset.filter(stock__gt=low)
    else:
        state = ""

    page_obj = Paginator(queryset.order_by("stock", "product__title", "pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {
        key: value
        for key, value in (("q", params.get("q", "")), ("state", state), ("product", product_id or ""))
        if value
    }
    return {
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "state": state,
        "states": STATES,
        "filters": filters,
        "qs": urlencode(filters),
        "low": low,
        "product_note": (
            Product.objects.filter(pk=product_id).values_list("title", flat=True).first() if product_id else ""
        ),
        "send_hint": queries.restock_send_hint(),
        "can_stock": True,
        "can_ledger": user.has_perm(LEDGER),
        "can_adjust": user.has_perm(ADJUST),
        "can_open_product": user.has_perm("catalog.change_product"),
    }


@panel_view(VIEW)
@require_GET
def inventory_list(request):
    context = _stock_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/inventory/_stock_results.html", context)
    return render(request, "panel/inventory/list.html", context)


def _ledger_context(params, user) -> dict:
    queryset = StockMovement.objects.select_related("variant__product")
    text = normalize_fa(params.get("q", ""), for_search=True)[:60]
    if text:
        queryset = queryset.filter(Q(variant__sku__icontains=text) | Q(variant__product__search_text__contains=text))
    reason = params.get("reason") if params.get("reason") in dict(StockMovement.REASON_CHOICES) else ""
    if reason:
        queryset = queryset.filter(reason=reason)
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))

    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    item_ids = [m.order_item_id for m in page_obj.object_list if m.order_item_id]
    numbers = dict(OrderItem.objects.filter(pk__in=item_ids).values_list("pk", "order__number")) if item_ids else {}
    filters = {
        key: value
        for key, value in (
            ("q", params.get("q", "")),
            ("reason", reason),
            ("from", params.get("from", "")),
            ("to", params.get("to", "")),
        )
        if value
    }
    return {
        "page_obj": page_obj,
        "rows": [(m, numbers.get(m.order_item_id)) for m in page_obj.object_list],
        "q": params.get("q", ""),
        "reason": reason,
        "reasons": StockMovement.REASON_CHOICES,
        "date_from": params.get("from", ""),
        "date_to": params.get("to", ""),
        "qs": urlencode(filters),
        "can_stock": user.has_perm(VIEW),
        "can_ledger": True,
        "can_orders": user.has_perm("orders.view_order"),
    }


@panel_view(LEDGER)
@require_GET
def inventory_ledger(request):
    context = _ledger_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/inventory/_ledger_results.html", context)
    return render(request, "panel/inventory/ledger.html", context)


@panel_view(VIEW, ADJUST)
@require_http_methods(["GET", "POST"])
def stock_adjust(request, variant_pk):
    variant = get_object_or_404(Variant.objects.select_related("product"), pk=variant_pk)
    params = request.POST if request.method == "POST" else request.GET
    hidden = [(key, value) for key, value in params.items() if key in LIST_PARAMS and value]
    form = StockAdjustForm(request.POST or None, variant=variant, initial={"expected": variant.stock})
    error = ""

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.adjust_stock(
                variant.pk,
                data["delta"],
                reason=normalize_fa(data["reason"]),
                by=request.user,
                expected_stock=data["expected"] if data["mode"] == "set" else None,
            )
        except StockConflict:
            variant.refresh_from_db(fields=["stock"])
            form = StockAdjustForm(variant=variant, initial={"expected": variant.stock})
            error = f"موجودی هم‌زمان تغییر کرد یا کافی نیست؛ موجودی فعلی {to_fa_digits(variant.stock)} است"
        else:
            audit.log(request.user, variant, audit.CHANGE, f"تغییر موجودی {variant.sku}: {data['delta']:+d}")
            if not request.htmx:
                htmx.flash(request, "موجودی ثبت شد")
                return redirect("panel:inventory")
            context = {**_stock_context(request.POST, request.user), "reset_modal": True}
            response = render(request, "panel/inventory/_stock_results.html", context)
            htmx.toast(response, "موجودی ثبت شد")
            return htmx.close_popover(response, "stock-modal")

    if request.method == "POST" and not request.htmx:
        htmx.flash(request, error or "اطلاعات را بررسی کنید", "error")
        return redirect("panel:inventory")
    response = render(
        request,
        "panel/inventory/_adjust_form.html",
        {
            "form": form,
            "variant": variant,
            "error": error,
            "hidden": hidden,
            "action": reverse("panel:stock_adjust", args=[variant.pk]),
        },
    )
    if request.method == "POST":
        retarget(response, "#stock-modal-body")
        reswap(response, "innerHTML")
    return response
