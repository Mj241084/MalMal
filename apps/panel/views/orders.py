"""Orders in the panel: list, detail and staff status moves (docs/09 module 2).

Every status change goes through workflow.change_status; this module never writes an Order itself.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts import ratelimit
from apps.core.jalali import to_fa_digits
from apps.orders import notify, shipping, workflow
from apps.orders.invoice import render_invoice
from apps.orders.models import PAID_STATES, Order
from apps.panel import audit, badges, htmx, queries
from apps.panel.forms import StatusChangeForm
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services
from apps.payments.models import Payment

PAGE_SIZE = 25
VIEW, MANAGE = "orders.view_order", "orders.manage_order_status"
TABS = (
    ("todo", "نیازمند اقدام", (Order.PAID, Order.PROCESSING)),
    ("shipped", "ارسال‌شده", (Order.SHIPPED,)),
    ("delivered", "تحویل‌شده", (Order.DELIVERED,)),
    ("closed", "لغو و بازگشت وجه", (Order.CANCELLED, Order.EXPIRED, Order.REFUNDED)),
    ("pending", "در انتظار پرداخت", (Order.PENDING,)),
    ("all", "همه", None),
)
TAB_STATUSES = {code: statuses for code, _label, statuses in TABS}
DONE = {
    Order.PROCESSING: "سفارش در حال آماده‌سازی است",
    Order.SHIPPED: "ارسال ثبت شد",
    Order.DELIVERED: "تحویل سفارش ثبت شد",
    Order.CANCELLED: "سفارش لغو شد",
}
RANK = {Order.PENDING: 1, Order.PAID: 2, Order.PROCESSING: 3, Order.SHIPPED: 4, Order.DELIVERED: 5}
STEP_LABELS = ("ثبت", "پرداخت", "آماده‌سازی", "ارسال", "تحویل")


# --- list -----------------------------------------------------------------


def _tab_counts() -> dict[str, int]:
    by_status = dict(Order.objects.order_by().values_list("status").annotate(n=Count("pk")))  # one query
    return {
        code: sum(by_status.values()) if statuses is None else sum(by_status.get(s, 0) for s in statuses)
        for code, _label, statuses in TABS
    }


def _list_context(params, user) -> dict:
    tab = params.get("tab") if params.get("tab") in TAB_STATUSES else "todo"
    queryset = Order.objects.all()
    if TAB_STATUSES[tab] is not None:
        queryset = queryset.filter(status__in=TAB_STATUSES[tab])
    condition = queries.order_search_q(params.get("q", ""))
    if condition is not None:
        queryset = queryset.filter(condition)
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))
    queryset = queryset.order_by("paid_at", "pk") if tab == "todo" else queryset.order_by("-created_at", "-pk")

    page_obj = Paginator(queryset, PAGE_SIZE).get_page(params.get("page"))
    counts = _tab_counts()
    filters = {key: params.get(key, "") for key in ("q", "from", "to") if params.get(key)}
    return {
        "tab": tab,
        "tabs": [(code, label, counts[code]) for code, label, _statuses in TABS],
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "date_from": params.get("from", ""),
        "date_to": params.get("to", ""),
        "filter_qs": urlencode(filters),
        "qs": urlencode({"tab": tab, **filters}),
        "hidden": [("tab", tab), ("page", page_obj.number), *filters.items()],
        "show_select": tab == "todo" and user.has_perm(MANAGE),
    }


@panel_view(VIEW)
@require_GET
def order_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/orders/_list_results.html", context)
    return render(request, "panel/orders/list.html", context)


@panel_view(VIEW, MANAGE)
@require_POST
def order_bulk(request):
    """«شروع آماده‌سازی» for the selected paid orders; also the one-click button of the dashboard queue."""
    numbers = set(request.POST.getlist("order")[:100])
    ids = Order.objects.filter(number__in=numbers, status=Order.PAID).values_list("pk", flat=True)
    done = 0
    for pk in list(ids):
        try:
            workflow.change_status(pk, Order.PROCESSING, by=request.user)
        except workflow.TransitionError:
            continue  # someone else moved it meanwhile
        done += 1
    badges.bust("orders_to_ship")
    skipped = len(numbers) - done
    message = to_fa_digits(f"{done} سفارش در حال آماده‌سازی شد" + (f"، {skipped} مورد مجاز نبود" if skipped else ""))
    level = "success" if done and not skipped else "warning"
    if not numbers:
        message, level = "سفارشی انتخاب نشده است", "error"

    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:orders")
    if request.POST.get("ctx") == "dashboard":
        response = render(request, "panel/partials/_ship_queue.html", queries.ship_queue(request.user))
    else:
        response = render(request, "panel/orders/_list_results.html", _list_context(request.POST, request.user))
    return htmx.toast(response, message, level)


# --- detail ---------------------------------------------------------------


def _load(number: str) -> Order:
    return get_object_or_404(
        Order.objects.select_related("shipping_method").prefetch_related("items", "payments", "status_logs__by_user"),
        number=number,
    )


def _steps(order: Order):
    rank = RANK.get(order.status)  # cancelled / expired / refunded show their own status instead
    return [(label, index <= rank) for index, label in enumerate(STEP_LABELS, 1)] if rank else None


def _detail_context(order: Order, user) -> dict:
    labels = dict(Order.STATUS_CHOICES)
    payments = list(order.payments.all())
    targets = workflow.allowed_targets(order)
    verified = [p for p in payments if p.status == Payment.VERIFIED]
    return {
        "order": order,
        "items": list(order.items.all()),
        "payments": payments,
        "refund_ids": set(payment_services.refund_candidates().filter(order=order).values_list("pk", flat=True)),
        "refund_payment": min(verified, key=lambda p: p.pk) if verified and Order.REFUNDED in targets else None,
        "logs": [
            {
                "log": log,
                "from_label": labels.get(log.from_status, ""),
                "to_label": labels.get(log.to_status, log.to_status),
                "by": (log.by_user.get_full_name() or log.by_user.mobile) if log.by_user else "",
            }
            for log in order.status_logs.all()
        ],
        "steps": _steps(order),
        "can_manage": user.has_perm(MANAGE),
        "can_refund": user.has_perms((MANAGE, "payments.view_payment")),
        "can_start": Order.PROCESSING in targets,
        "can_ship": Order.SHIPPED in targets,
        "can_deliver": Order.DELIVERED in targets,
        "can_cancel": Order.CANCELLED in targets,
        "can_invoice": order.status in PAID_STATES,
        "can_resend": notify.has_status_sms(order),
        "needs_tracking": shipping.has_tracking(order),
        "tracking_page": shipping.tracking_page(order),
        "recipient_text": shipping.recipient_text(order),
        "map_link": shipping.map_link(order),
    }


def _detail_response(request, number: str, message: str = "", level: str = "success"):
    """Errors are answered with 200 too: htmx does not swap 4xx, and the toast carries the message."""
    if not request.htmx:
        if message:
            htmx.flash(request, message, level)
        return redirect("panel:order_detail", number=number)
    response = render(request, "panel/orders/_detail_body.html", _detail_context(_load(number), request.user))
    return htmx.toast(response, message, level) if message else response


@panel_view(VIEW)
@require_GET
def order_detail(request, number):
    return render(request, "panel/orders/detail.html", _detail_context(_load(number), request.user))


@panel_view(VIEW, MANAGE)
@require_POST
def order_status(request, number):
    order = get_object_or_404(Order, number=number)
    form = StatusChangeForm(request.POST)
    if not form.is_valid():
        return _detail_response(request, number, form.first_error(), "error")
    data = form.cleaned_data
    try:
        workflow.change_status(
            order.pk, data["to"], by=request.user, tracking_code=data["tracking_code"], note=data["note"]
        )
    except workflow.TransitionError as exc:  # illegal move, missing tracking code, or a stale page
        return _detail_response(request, number, str(exc), "error")
    badges.bust("orders_to_ship")
    badges.bust("refunds")
    return _detail_response(request, number, DONE[data["to"]])


@panel_view(VIEW, MANAGE)
@require_POST
def order_resend_sms(request, number):
    order = get_object_or_404(Order.objects.select_related("shipping_method"), number=number)
    if not notify.has_status_sms(order):
        return _detail_response(request, number, "برای این وضعیت پیامکی تعریف نشده است", "error")
    if not ratelimit.consume(f"panel:sms:{order.pk}", 3, ratelimit.HOUR):
        return _detail_response(
            request, number, "پیامک این سفارش در ساعت گذشته چند بار ارسال شده؛ بعداً تلاش کنید", "error"
        )
    notify.send_status_sms(order.pk)  # no transaction is open here
    audit.log(request.user, order, audit.CHANGE, "ارسال دوباره‌ی پیامک وضعیت")
    return _detail_response(request, number, "پیامک ارسال شد؛ نتیجه در لاگ پیامک ثبت می‌شود")


@panel_view(VIEW)
@require_GET
def order_invoice(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number, status__in=PAID_STATES)
    return render_invoice(request, order)
