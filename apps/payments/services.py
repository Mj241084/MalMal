"""Payment lifecycle: start, callback, finalize (docs/02 §7). No network call ever runs inside a transaction."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.cart import services as cart_services
from apps.cart.models import CartItem
from apps.engagement import counters
from apps.notifications import sms
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments import gateways
from apps.payments.models import Payment

logger = logging.getLogger(__name__)


class PaymentStartError(Exception):
    """The gateway could not be reached or refused the request."""


@dataclass(frozen=True)
class Outcome:
    # paid | cancelled | failed | processing | retry | paid_no_stock | duplicate | unknown
    state: str
    order: Order | None = None


def _move(payment_id: int, expected: Iterable[str], **fields) -> bool:
    """Conditional status change: True only for the caller that actually moved it."""
    return bool(
        Payment.objects.filter(pk=payment_id, status__in=list(expected)).update(updated_at=timezone.now(), **fields)
    )


def requeue_stale_verifying() -> int:
    cutoff = timezone.now() - Payment.VERIFY_STALE
    return Payment.objects.filter(status=Payment.VERIFYING, updated_at__lt=cutoff).update(
        status=Payment.REDIRECTED, updated_at=timezone.now()
    )


def start(order: Order, gateway_code: str, *, ip: str | None = None) -> str:
    """Record the Payment first, then ask the gateway (outside any transaction). Returns the URL to redirect to."""
    if not order.can_pay_now:
        raise PaymentStartError("order is not payable")
    try:
        adapter = gateways.adapter_for(gateway_code)
    except KeyError as exc:
        raise PaymentStartError(f"unknown gateway {gateway_code!r}") from exc

    payment = Payment.objects.create(order=order, gateway_code=gateway_code, amount=order.payable, ip=ip)
    callback = f"{settings.SITE_URL}{reverse('payments:callback', args=[gateway_code])}"
    try:
        result = adapter.request(
            amount=payment.amount,
            callback_url=callback,
            description=f"سفارش {order.number}",
            mobile=order.buyer_mobile,
            order_number=order.number,
        )
    except gateways.GatewayError as exc:
        _move(payment.pk, [Payment.INITIATED], status=Payment.FAILED, request_payload={"error": str(exc)})
        logger.warning("Payment %s could not start: %s", payment.pk, exc)
        raise PaymentStartError(str(exc)) from exc
    _move(
        payment.pk,
        [Payment.INITIATED],
        status=Payment.REDIRECTED,
        authority=result.authority,
        request_payload=result.payload,
    )
    return result.redirect_url


def handle_callback(gateway_code: str, params) -> Outcome:
    """Idempotent: any number of callbacks for one authority pay the order at most once."""
    adapter = gateways.adapter_for(gateway_code)  # KeyError -> the view answers 404
    authority, reported_ok = adapter.parse_callback(params)
    payment = (
        Payment.objects.select_related("order").filter(gateway_code=gateway_code, authority=authority).first()
        if authority
        else None
    )
    if payment is None:
        return Outcome("unknown")
    order = payment.order
    if payment.status == Payment.VERIFIED:
        return Outcome("paid", order)
    if not reported_ok:
        _move(payment.pk, [Payment.INITIATED, Payment.REDIRECTED], status=Payment.CANCELLED)
        return Outcome("cancelled", order)

    # Claim. CANCELLED is claimable on purpose: our own "superseded" cancel must not lose a payment the customer
    # still completes at the bank.
    if not _move(payment.pk, [Payment.REDIRECTED, Payment.CANCELLED], status=Payment.VERIFYING):
        payment.refresh_from_db()
        state = {Payment.VERIFIED: "paid", Payment.FAILED: "failed"}.get(payment.status, "processing")
        return Outcome(state, order)

    result = adapter.verify(authority=authority, amount=payment.amount)  # network: no transaction is open here
    if result.retryable:
        _move(payment.pk, [Payment.VERIFYING], status=Payment.REDIRECTED)
        return Outcome("retry", order)
    if not result.ok:
        _move(payment.pk, [Payment.VERIFYING], status=Payment.FAILED, verify_payload=result.payload)
        logger.warning("Payment %s was not verified: %s", payment.pk, result.payload)
        return Outcome("failed", order)
    return Outcome(_finalize(payment.pk, result), order)


def _finalize(payment_id: int, result: gateways.VerifyResult) -> str:
    now = timezone.now()
    with transaction.atomic():
        if not _move(
            payment_id,
            [Payment.VERIFYING],
            status=Payment.VERIFIED,
            ref_id=result.ref_id,
            card_pan_masked=result.card_pan,
            verify_payload=result.payload,
            verified_at=now,
        ):
            return "paid"  # a concurrent callback already finished it
        payment = Payment.objects.select_related("order").get(pk=payment_id)
        order = payment.order

        if order.status in (Order.EXPIRED, Order.CANCELLED):
            # Money was taken after the reservation ended: take the stock back, or tell a human.
            if not order_services.reserve_again(order):
                logger.error(
                    "Order %s was paid (payment %s) but its stock is gone: refund needed",
                    order.number,
                    payment.pk,
                )
                return "paid_no_stock"
        elif order.status != Order.PENDING:
            logger.error("Order %s is already %s: payment %s must be refunded", order.number, order.status, payment.pk)
            return "duplicate"

        order_services.transition(
            order.pk,
            expected=order.status,
            to=Order.PAID,
            note=f"payment {payment.pk}",
            paid_at=now,
            reserved_until=None,
        )
        items = list(order.items.all())
        per_product: dict[int, int] = {}
        for item in items:
            if item.product_id:
                per_product[item.product_id] = per_product.get(item.product_id, 0) + item.qty
        counters.add_purchases(per_product)
        # Only the purchased variants leave the cart: lines added after checkout started stay.
        CartItem.objects.filter(
            cart__user_id=order.user_id, variant_id__in=[i.variant_id for i in items if i.variant_id]
        ).delete()
        cart_services.bust_count(order.user_id)
        transaction.on_commit(lambda: _notify_paid(order.pk))
    return "paid"


def _notify_paid(order_id: int) -> None:
    order = Order.objects.get(pk=order_id)
    try:
        sms.send_template("order_paid", order.buyer_mobile, {"ORDER": order.number, "AMOUNT": f"{order.payable:,}"})
    except Exception:  # an SMS problem must never touch the order (docs/05 §4)
        logger.exception("order_paid SMS failed for %s", order.number)
