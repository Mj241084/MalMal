"""Payments in the panel: the refund report, and the one place a refund is recorded (docs/09 module 3)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.text import normalize_fa
from apps.panel import audit, auth, htmx, queries
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services
from apps.payments.models import Payment

PAGE_SIZE = 25
VIEW, MANAGE = "payments.view_payment", "orders.manage_order_status"


def _list_context(params, user) -> dict:
    tab = "all" if params.get("tab") == "all" else "refund"
    base = payment_services.refund_candidates() if tab == "refund" else Payment.objects.all()
    queryset = base.select_related("order")
    if params.get("status") in dict(Payment.STATUS_CHOICES):
        queryset = queryset.filter(status=params["status"])
    if params.get("gateway"):
        queryset = queryset.filter(gateway_code=params["gateway"])
    text = normalize_fa(params.get("q", ""))[:40]
    if text:
        queryset = queryset.filter(
            Q(order__number__icontains=text) | Q(authority__icontains=text) | Q(ref_id__icontains=text)
        )
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))

    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {key: params.get(key, "") for key in ("q", "status", "gateway", "from", "to") if params.get(key)}
    can_refund = user.has_perm(MANAGE)
    candidate_ids = (
        set(
            payment_services.refund_candidates()
            .filter(pk__in=[p.pk for p in page_obj.object_list])
            .values_list("pk", flat=True)
        )
        if can_refund
        else set()
    )
    return {
        "tab": tab,
        "tabs": [
            ("refund", "نیازمند بازگشت وجه", payment_services.refund_candidates().count()),
            ("all", "همه", Payment.objects.count()),
        ],
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "date_from": params.get("from", ""),
        "date_to": params.get("to", ""),
        "status": params.get("status", ""),
        "gateway": params.get("gateway", ""),
        "status_choices": Payment.STATUS_CHOICES,
        "gateways": sorted(set(Payment.objects.order_by().values_list("gateway_code", flat=True))),
        "filter_qs": urlencode(filters),
        "qs": urlencode({"tab": tab, **filters}),
        "hidden": [("tab", tab), ("page", page_obj.number), *filters.items()],
        "can_refund": can_refund,
        "candidate_ids": candidate_ids,
    }


@panel_view(VIEW)
@require_GET
def payment_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/payments/_list_results.html", context)
    return render(request, "panel/payments/list.html", context)


@panel_view(VIEW, MANAGE)
@require_POST
def payment_refund(request, pk):
    """The only write of the payments section; the rules live in payments.services.record_refund."""
    get_object_or_404(Payment, pk=pk)
    note = " ".join(request.POST.get("note", "").split())[:200]
    if request.POST.get("confirm") != "1":
        message, level = "تایید کنید که مبلغ را از درگاه برگردانده‌اید", "error"
    else:
        try:
            result = payment_services.record_refund(pk, by=request.user, note=note)
        except payment_services.RefundError as exc:
            message, level = str(exc), "error"
        else:
            audit.log(request.user, result.payment, audit.CHANGE, f"بازگشت وجه ثبت شد: {note}")
            message, level = "بازگشت وجه ثبت شد", "success"

    if request.htmx:  # only the payments list posts with HTMX; the order page posts normally
        response = render(request, "panel/payments/_list_results.html", _list_context(request.POST, request.user))
        return htmx.toast(response, message, level)
    htmx.flash(request, message, level)
    return redirect(auth.safe_next(request, request.POST.get("next")))
