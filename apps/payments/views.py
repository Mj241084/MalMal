"""Gateway callback and the DEBUG-only fake bank page."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.payments import gateways, services

OUTCOME_MESSAGES = {
    "paid": (messages.SUCCESS, "پرداخت با موفقیت انجام شد"),
    "cancelled": (
        messages.ERROR,
        "پرداخت انجام نشد یا لغو شد. تا پایان مهلت رزرو می‌توانید دوباره پرداخت کنید",
    ),
    "failed": (
        messages.ERROR,
        "پرداخت تایید نشد. اگر مبلغی از حساب شما کسر شده، تا چند ساعت بازگردانده می‌شود",
    ),
    "paid_no_stock": (
        messages.ERROR,
        "پرداخت انجام شد اما موجودی کالا تمام شده است. با پشتیبانی تماس بگیرید",
    ),
    "duplicate": (messages.ERROR, "این سفارش قبلاً پرداخت شده بود. با پشتیبانی تماس بگیرید"),
}


@require_GET
def callback_view(request, code):
    try:
        gateways.adapter_for(code)
    except KeyError as exc:
        raise Http404 from exc
    outcome = services.handle_callback(code, request.GET)
    if outcome.order is None:
        messages.error(request, "پرداخت پیدا نشد")
        return redirect("orders:list")
    if outcome.state in ("processing", "retry"):
        return render(request, "pages/payments/processing.html", {"retry_url": request.get_full_path()})
    level, text = OUTCOME_MESSAGES[outcome.state]
    messages.add_message(request, level, text)
    return redirect("orders:result", number=outcome.order.number)


@require_GET
def fake_bank_view(request, authority):
    if not settings.DEBUG:
        raise Http404
    return render(
        request,
        "pages/payments/fake_bank.html",
        {"authority": authority, "callback": reverse("payments:callback", args=["fake"])},
    )
