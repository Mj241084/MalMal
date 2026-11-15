"""Staff-driven order status changes (docs/02 §7).

One place owns the allowed moves, the stock and counter effects, and the SMS that follows.
Customer and system moves (place, pay, expire, supersede) stay in services.py and payments.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import StockMovement
from apps.core.text import normalize_digits
from apps.engagement import counters
from apps.orders import notify, services, shipping
from apps.orders.models import Order
from apps.payments.models import Payment

MAX_TRACKING_LENGTH = 25  # sms.ir parameter limit (error 114)

MOVES = {
    Order.PAID: (Order.PROCESSING, Order.CANCELLED),
    Order.PROCESSING: (Order.SHIPPED, Order.CANCELLED),
    Order.SHIPPED: (Order.DELIVERED,),
    Order.DELIVERED: (Order.REFUNDED,),
    Order.CANCELLED: (Order.REFUNDED,),
    Order.EXPIRED: (Order.REFUNDED,),
}
NEEDS_PAYMENT = (Order.CANCELLED, Order.EXPIRED)  # refunded only makes sense when money was actually taken


class TransitionError(Exception):
    """The move is not allowed; the message is shown to the staff member."""


def allowed_targets(order) -> list[str]:
    if order.status in NEEDS_PAYMENT and not order.payments.filter(status=Payment.VERIFIED).exists():
        return []
    return list(MOVES.get(order.status, ()))


def _withdraw_purchases(order) -> None:
    per_product: dict[int, int] = {}
    for item in order.items.all():
        if item.product_id:
            per_product[item.product_id] = per_product.get(item.product_id, 0) + item.qty
    counters.remove_purchases(per_product, order.paid_at)


def change_status(order_id: int, to: str, *, by, tracking_code: str = "", note: str = "") -> None:
    tracking_code = normalize_digits(tracking_code).strip()
    with transaction.atomic():
        order = Order.objects.select_related("shipping_method").get(pk=order_id)
        if to not in allowed_targets(order):
            raise TransitionError("این تغییر وضعیت مجاز نیست")

        fields: dict = {}
        if to == Order.SHIPPED:
            if shipping.has_tracking(order) and not tracking_code:
                raise TransitionError("برای این روش ارسال، کد رهگیری الزامی است")
            if len(tracking_code) > MAX_TRACKING_LENGTH:
                raise TransitionError(f"کد رهگیری حداکثر {MAX_TRACKING_LENGTH} نویسه است")
            fields["tracking_code"] = tracking_code
        elif to == Order.CANCELLED:
            fields.update(cancelled_at=timezone.now(), cancel_reason=note[:200])

        previous = order.status
        if not services.transition(order.pk, expected=previous, to=to, note=note, by=by, **fields):
            raise TransitionError("وضعیت سفارش هم‌زمان تغییر کرد؛ صفحه را دوباره باز کنید")

        if to == Order.CANCELLED:  # exactly once: only the caller that won the conditional update gets here
            services.release_stock(order, StockMovement.REASON_CANCEL)
            _withdraw_purchases(order)
        elif to == Order.REFUNDED and previous == Order.DELIVERED:
            _withdraw_purchases(order)

        transaction.on_commit(lambda: notify.send_status_sms(order_id))
