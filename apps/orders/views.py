"""Checkout, order list/detail and payment restart (docs/02 §6-8)."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.forms import AddressForm
from apps.accounts.models import Address
from apps.accounts.services import save_new_address
from apps.cart import services as cart_services
from apps.core.decorators import login_required_htmx
from apps.core.http import client_ip
from apps.orders import services
from apps.orders.forms import CheckoutBuyerForm
from apps.orders.invoice import render_invoice
from apps.orders.models import PAID_STATES, Order
from apps.orders.shipping import default_method, tracking_page
from apps.payments import gateways
from apps.payments import services as payment_services


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _neshan_context() -> dict:
    return {
        "neshan_map_key": settings.NESHAN_MAP_KEY,
        "neshan_service_enabled": bool(settings.NESHAN_SERVICE_KEY),
    }


def _addresses(user) -> list[Address]:
    queryset = Address.objects.filter(user=user, deleted_at__isnull=True).select_related("province", "city")
    return list(queryset.order_by("-is_default", "id"))


def _default_address_id(addresses: list[Address]) -> int | None:
    return next((a.pk for a in addresses if a.is_default), addresses[0].pk if addresses else None)


def _buyer_form(user, data=None):
    form = CheckoutBuyerForm(data, user=user)
    return form if form.fields else None


def _address_section_context(user, *, selected=None, address_form=None) -> dict:
    addresses = _addresses(user)
    return {
        "addresses": addresses,
        "selected_address_id": selected or _default_address_id(addresses),
        "address_form": address_form,
        "form_action": reverse("orders:address_new"),
        "form_target": "#checkout-addresses",
        **_neshan_context(),
    }


def _checkout_page(request, *, buyer_form, errors=(), selected_address_id=None, selected_gateway=""):
    lines, notices = cart_services.normalize(cart_services.get_cart(request.user))
    if not lines:
        return redirect("cart:detail")
    summary = cart_services.summarize(lines)
    method = default_method()
    options = gateways.available(summary.items_total)
    context = {
        "lines": lines,
        "notices": notices,
        "summary": summary,
        "method": method,
        "fingerprint": cart_services.fingerprint(lines),
        "buyer_form": buyer_form,
        "errors": list(errors),
        "gateways": options,
        "selected_gateway": selected_gateway or (options[0].code if options else ""),
        **_address_section_context(request.user, selected=selected_address_id),
    }
    return render(request, "pages/checkout.html", context)


@login_required_htmx
@require_GET
def checkout_view(request):
    return _checkout_page(request, buyer_form=_buyer_form(request.user))


def _pay(request, order: Order, gateway_code: str):
    try:
        url = payment_services.start(order, gateway_code, ip=client_ip(request))
    except payment_services.PaymentStartError:
        messages.error(request, "اتصال به درگاه برقرار نشد. از صفحه‌ی سفارش دوباره پرداخت کنید")
        return redirect("orders:detail", number=order.number)
    return redirect(url)


@login_required_htmx
@require_POST
def place_view(request):
    user = request.user
    method = default_method()
    buyer_form = _buyer_form(user, request.POST)
    address = (
        Address.objects.filter(pk=_int(request.POST.get("address_id")), user=user, deleted_at__isnull=True)
        .select_related("province", "city")
        .first()
    )
    lines, _ = cart_services.normalize(cart_services.get_cart(user))
    allowed = {g.code for g in gateways.available(cart_services.summarize(lines).items_total)}
    gateway_code = request.POST.get("gateway", "")

    errors = []
    if method is None:
        errors.append("ارسال در حال حاضر ممکن نیست")
    if address is None:
        errors.append("آدرس تحویل را انتخاب کنید" if _addresses(user) else "ابتدا یک آدرس تحویل ثبت کنید")
    if gateway_code not in allowed:
        errors.append("روش پرداخت را انتخاب کنید")
    if buyer_form is not None and not buyer_form.is_valid():
        errors.append("اطلاعات خریدار را کامل و درست وارد کنید")

    if not errors:
        try:
            order = services.place_order(
                user=user,
                address=address,
                method=method,
                buyer_form=buyer_form,
                seen_fingerprint=request.POST.get("fingerprint", ""),
            )
        except services.CheckoutError as exc:
            errors.append(str(exc))
            user.refresh_from_db()  # the rolled-back profile save must not leak into the re-rendered page
        else:
            return _pay(request, order, gateway_code)

    return _checkout_page(
        request,
        buyer_form=buyer_form,
        errors=errors,
        selected_address_id=address.pk if address else None,
        selected_gateway=gateway_code,
    )


@login_required_htmx
@require_http_methods(["GET", "POST"])
def address_new_view(request):
    """Inline address creation inside checkout: the form on GET, the refreshed address section on POST."""
    if request.method == "POST":
        form = AddressForm(request.POST, user=request.user)
        if form.is_valid():
            address = save_new_address(request.user, form)
            return render(
                request,
                "partials/_checkout_addresses.html",
                _address_section_context(request.user, selected=address.pk),
            )
        return render(
            request,
            "partials/_checkout_addresses.html",
            _address_section_context(request.user, address_form=form),
        )
    context = {
        "form": AddressForm(user=request.user),
        "form_action": reverse("orders:address_new"),
        "form_target": "#checkout-addresses",
        **_neshan_context(),
    }
    return render(request, "partials/_address_form.html", context)


# --- orders ----------------------------------------------------------------


def _order_context(request, number: str, **extra) -> dict:
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number, user=request.user)
    return {
        "order": order,
        "gateways": gateways.available(order.payable) if order.can_pay_now else [],
        "invoice_url": reverse("orders:invoice", args=[order.number]) if order.status in PAID_STATES else "",
        "tracking_page": tracking_page(order),
        **extra,
    }


@login_required_htmx
@require_GET
def invoice_view(request, number):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"), number=number, user=request.user, status__in=PAID_STATES
    )
    return render_invoice(request, order)


@login_required_htmx
@require_GET
def order_list_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")[:50]
    return render(request, "pages/orders.html", {"orders": orders})


@login_required_htmx
@require_GET
def order_detail_view(request, number):
    return render(request, "pages/order_detail.html", _order_context(request, number))


@login_required_htmx
@require_GET
def order_result_view(request, number):
    return render(request, "pages/order_detail.html", _order_context(request, number, result=True))


@login_required_htmx
@require_POST
def pay_view(request, number):
    order = get_object_or_404(Order, number=number, user=request.user)
    allowed = [g.code for g in gateways.available(order.payable)]
    code = request.POST.get("gateway")
    code = code if code in allowed else (allowed[0] if allowed else "")
    if not order.can_pay_now or not code:
        messages.error(request, "این سفارش قابل پرداخت نیست")
        return redirect("orders:detail", number=number)
    return _pay(request, order, code)
