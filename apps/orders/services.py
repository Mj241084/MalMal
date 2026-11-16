"""Order lifecycle: place, expire, release stock. Money and stock rules live here (docs/02 §7)."""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.cart import services as cart_services
from apps.catalog import stock
from apps.catalog.models import StockMovement
from apps.orders.models import Order, OrderItem, OrderStatusLog
from apps.payments.models import Payment

logger = logging.getLogger(__name__)

ORDER_RESERVE = timedelta(minutes=30)  # C5 [ASSUMPTION]
PAYMENT_GRACE = timedelta(minutes=20)  # reservation floor while the customer is at the bank

CHANGED = "قیمت یا موجودی برخی کالاها تغییر کرده است. خلاصه‌ی سفارش را بررسی و دوباره تایید کنید"


class CheckoutError(Exception):
    """The order cannot be placed. `changed=True` means what is on screen is stale."""

    def __init__(self, message: str, *, changed: bool = False):
        super().__init__(message)
        self.changed = changed


def new_number() -> str:
    while True:  # inside an IMMEDIATE transaction: no concurrent writer can take the same number
        number = f"ML-{secrets.randbelow(10**8):08d}"
        if not Order.objects.filter(number=number).exists():
            return number


def log(order_id: int, from_status: str, to_status: str, note: str = "", by=None) -> None:
    OrderStatusLog.objects.create(
        order_id=order_id, from_status=from_status, to_status=to_status, note=note, by_user=by
    )


def transition(order_id: int, *, expected: str, to: str, note: str = "", by=None, **fields) -> bool:
    """Conditional status change: True only for the caller that actually moved it."""
    updated = Order.objects.filter(pk=order_id, status=expected).update(status=to, updated_at=timezone.now(), **fields)
    if updated:
        log(order_id, expected, to, note, by)
    return bool(updated)


def _image_path(product) -> str:
    image = product.main_image
    if image is None:
        return ""
    if image.widths:
        return image.widths[min(image.widths, key=int)]
    return image.image.name if image.image else ""


def release_stock(order: Order, reason: str) -> None:
    product_ids = []
    for item in order.items.exclude(variant=None):
        stock.increment(item.variant_id, item.qty, reason=reason, order_item_id=item.pk, note=order.number)
        product_ids.append(item.product_id)
    stock.refresh_products(p for p in product_ids if p)


def reserve_again(order: Order) -> bool:
    """Late payment on an expired order: take the stock back, or report that it is gone."""
    if order.items.filter(variant=None).exists():
        return False
    try:
        with transaction.atomic():
            for item in order.items.all():
                stock.decrement(
                    item.variant_id,
                    item.qty,
                    reason=StockMovement.REASON_ORDER,
                    order_item_id=item.pk,
                    note="late payment",
                )
    except stock.InsufficientStock:
        return False
    stock.refresh_products(item.product_id for item in order.items.all() if item.product_id)
    return True


def extend_reservation(order_id: int) -> None:
    """Keep the stock for the customer while they are at the bank (capped, so it cannot be held forever)."""
    order = Order.objects.filter(pk=order_id, status=Order.PENDING).first()
    if order is None:
        return
    target = min(timezone.now() + PAYMENT_GRACE, order.created_at + ORDER_RESERVE + PAYMENT_GRACE)
    if order.reserved_until is None or order.reserved_until < target:
        Order.objects.filter(pk=order_id, status=Order.PENDING).update(reserved_until=target, updated_at=timezone.now())


def cancel_pending(order: Order, *, reason: str) -> bool:
    if not transition(
        order.pk,
        expected=Order.PENDING,
        to=Order.CANCELLED,
        note=reason,
        cancelled_at=timezone.now(),
        cancel_reason=reason,
    ):
        return False
    order.payments.filter(status__in=[Payment.INITIATED, Payment.REDIRECTED]).update(status=Payment.CANCELLED)
    release_stock(order, StockMovement.REASON_CANCEL)
    return True


def expire_order(order_id: int) -> bool:
    """Idempotent. Skips orders whose payment is being verified right now."""
    with transaction.atomic():
        order = Order.objects.filter(pk=order_id, status=Order.PENDING, reserved_until__lt=timezone.now()).first()
        if order is None or order.payments.filter(status=Payment.VERIFYING).exists():
            return False
        if not transition(order.pk, expected=Order.PENDING, to=Order.EXPIRED, note="reservation expired"):
            return False
        # same transaction as the status flip: released exactly once
        release_stock(order, StockMovement.REASON_EXPIRE)
    return True


def place_order(*, user, address, method, buyer_form, seen_fingerprint: str) -> Order:
    """Revalidate everything from the database, reserve stock atomically, snapshot the order."""
    try:
        with transaction.atomic():
            lines, _ = cart_services.normalize(cart_services.get_cart(user))
            summary = cart_services.summarize(lines)
            if not lines:
                raise CheckoutError("سبد خرید خالی است")
            if summary.has_unavailable:
                raise CheckoutError("کالای ناموجود را از سبد خرید حذف کنید", changed=True)
            if cart_services.fingerprint(lines) != seen_fingerprint:
                raise CheckoutError(CHANGED, changed=True)

            for pending in Order.objects.filter(user=user, status=Order.PENDING):
                if pending.payments.filter(status=Payment.VERIFYING).exists():
                    raise CheckoutError("پرداخت قبلی شما در حال بررسی است؛ چند دقیقه بعد دوباره تلاش کنید")
                cancel_pending(pending, reason="superseded")

            if buyer_form is not None:
                buyer_form.apply_to(user)
            if not (user.first_name and user.last_name and user.national_code):
                raise CheckoutError("اطلاعات خریدار را کامل کنید")

            order = Order.objects.create(
                number=new_number(),
                user=user,
                items_total=summary.items_total,
                shipping_cost=0,  # collect mode (07): the customer pays Tipax on delivery
                payable=summary.items_total,
                buyer_name=user.get_full_name(),
                buyer_mobile=user.mobile,
                buyer_national_code=user.national_code,
                buyer_email=user.email,
                recipient_name=address.recipient_name,
                recipient_mobile=address.recipient_mobile,
                province_name=address.province.name,
                city_name=address.city.name,
                address_text=address.address_text,
                plate=address.plate,
                unit=address.unit,
                postal_code=address.postal_code,
                lat=address.lat,
                lng=address.lng,
                shipping_method=method,
                shipping_method_title=method.title,
                shipping_payment_mode=method.payment_mode,
                reserved_until=timezone.now() + ORDER_RESERVE,
            )
            for line in lines:
                variant, product = line.variant, line.variant.product
                item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    product_title=product.title,
                    variant_title=variant.title,
                    sku=variant.sku,
                    unit_price=variant.price,
                    qty=line.qty,
                    image_path=_image_path(product),
                    warranty_text=product.warranty_text,
                )
                try:
                    stock.decrement(
                        variant.pk,
                        line.qty,
                        reason=StockMovement.REASON_ORDER,
                        order_item_id=item.pk,
                        note=order.number,
                    )
                except stock.InsufficientStock as exc:
                    raise CheckoutError(CHANGED, changed=True) from exc
            stock.refresh_products(line.variant.product_id for line in lines)
            log(order.pk, "", Order.PENDING, "created")
    except DjangoValidationError as exc:  # the D20 national-code lock raised by User.save()
        raise CheckoutError("اطلاعات خریدار را کامل و درست وارد کنید") from exc
    return order
