"""Customers in the panel (docs/09 module 11). The national-code lock (D20) opens only here: permission, reason, audit."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts import services
from apps.accounts.models import User
from apps.engagement.models import Like, Review, StockSubscription
from apps.orders.models import PAID_STATES, Order
from apps.panel import audit, htmx, queries
from apps.panel.forms_settings import NationalCodeForm, first_error
from apps.panel.permissions import panel_view

PAGE_SIZE = 25
VIEW, CHANGE, NATIONAL = "accounts.view_user", "accounts.change_user", "accounts.change_national_code"


def _list_context(params) -> dict:
    queryset = User.objects.filter(is_staff=False).annotate(
        order_count=Count("orders", filter=~Q(orders__status=Order.PENDING)),
        spent=Sum("orders__payable", filter=Q(orders__status__in=PAID_STATES)),
    )
    condition = queries.customer_search_q(params.get("q", ""))
    if condition is not None:
        queryset = queryset.filter(condition)
    state = "inactive" if params.get("state") == "inactive" else ""
    if state:
        queryset = queryset.filter(is_active=False)
    page_obj = Paginator(queryset.order_by("-date_joined", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {key: value for key, value in (("q", params.get("q", "")), ("state", state)) if value}
    return {"page_obj": page_obj, "q": params.get("q", ""), "state": state, "qs": urlencode(filters)}


@panel_view(VIEW)
@require_GET
def customer_list(request):
    context = _list_context(request.GET)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/customers/_list_results.html", context)
    return render(request, "panel/customers/list.html", context)


def _customer(pk) -> User:
    return get_object_or_404(User, pk=pk, is_staff=False)


@panel_view(VIEW)
@require_GET
def customer_detail(request, pk):
    customer = _customer(pk)
    user = request.user
    paid = Order.objects.filter(user=customer, status__in=PAID_STATES).aggregate(n=Count("pk"), total=Sum("payable"))
    context = {
        "customer": customer,
        "paid_count": paid["n"],
        "spent": paid["total"] or 0,
        "order_count": Order.objects.filter(user=customer).exclude(status=Order.PENDING).count(),
        "orders": list(Order.objects.filter(user=customer).order_by("-created_at", "-pk")[:10]),
        "addresses": list(customer.addresses.filter(deleted_at__isnull=True).select_related("province", "city")),
        "reviews": list(Review.objects.filter(user=customer).select_related("product").order_by("-created_at")[:10]),
        "like_count": Like.objects.filter(user=customer).count(),
        "likes": list(Like.objects.filter(user=customer).select_related("product").order_by("-created_at")[:10]),
        "subscriptions": list(
            StockSubscription.objects.filter(user=customer, notified_at__isnull=True)
            .select_related("variant__product")
            .order_by("-created_at")[:10]
        ),
        "can_change": user.has_perm(CHANGE),
        "can_national": user.has_perm(NATIONAL),
        "can_orders": user.has_perm("orders.view_order"),
        "nc_form": NationalCodeForm(),
    }
    return render(request, "panel/customers/detail.html", context)


@panel_view(VIEW, CHANGE)
@require_POST
def customer_active(request, pk):
    customer = _customer(pk)
    active = request.POST.get("to") == "1"
    services.set_customer_active(customer, active)
    audit.log(request.user, customer, audit.CHANGE, "فعال‌سازی حساب" if active else "غیرفعال‌سازی حساب")
    htmx.flash(request, "حساب فعال شد" if active else "حساب غیرفعال شد؛ مشتری دیگر نمی‌تواند وارد شود")
    return redirect("panel:customer_detail", pk=pk)


@panel_view(VIEW, CHANGE)
@require_POST
def customer_logout(request, pk):
    customer = _customer(pk)
    services.revoke_sessions(customer)
    audit.log(request.user, customer, audit.CHANGE, "خروج از همه‌ی دستگاه‌ها")
    htmx.flash(request, "مشتری از همه‌ی دستگاه‌ها خارج شد")
    return redirect("panel:customer_detail", pk=pk)


@panel_view(VIEW, NATIONAL)
@require_POST
def customer_national_code(request, pk):
    customer = _customer(pk)
    form = NationalCodeForm(request.POST)
    if not form.is_valid():
        htmx.flash(request, first_error(form), "error")
        return redirect("panel:customer_detail", pk=pk)
    data = form.cleaned_data
    try:
        previous = services.change_national_code(customer, data["code"])
    except services.CustomerError as exc:
        htmx.flash(request, str(exc), "error")
        return redirect("panel:customer_detail", pk=pk)
    audit.log(
        request.user, customer, audit.CHANGE, f"تغییر کد ملی از {previous or 'خالی'} به {data['code']}: {data['note']}"
    )
    htmx.flash(request, "کد ملی تغییر کرد")
    return redirect("panel:customer_detail", pk=pk)
