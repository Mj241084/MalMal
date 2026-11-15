"""Order status SMS. Runs after commit and never raises (docs/05 §4)."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.core.validators import normalize_iran_mobile
from apps.notifications import sms
from apps.orders import shipping
from apps.orders.models import Order


def admin_mobiles() -> list[str]:
    result = []
    for raw in settings.SMS_ADMIN_MOBILES.split(","):
        try:
            result.append(normalize_iran_mobile(raw))
        except ValidationError:
            continue
    return result


def _message(order: Order) -> tuple[str, dict] | None:
    base = {"ORDER": order.number}
    if order.status == Order.SHIPPED:
        if shipping.has_tracking(order):
            return "order_shipped", {**base, "CARRIER": order.shipping_method_title, "TRACKING": order.tracking_code}
        return "order_shipped_courier", base
    if order.status == Order.DELIVERED:
        return "order_delivered", base
    if order.status == Order.CANCELLED:
        return "order_cancelled", base
    if order.status == Order.REFUNDED:
        return "order_refunded", {**base, "AMOUNT": f"{order.payable:,}"}
    return None


def send_status_sms(order_id: int) -> None:
    """The SMS for the order's *current* status (after a change, and for the admin «resend» action)."""
    order = Order.objects.select_related("shipping_method").get(pk=order_id)
    message = _message(order)
    if message:
        sms.send_safely(message[0], order.buyer_mobile, message[1])
