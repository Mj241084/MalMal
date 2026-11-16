import pytest

from apps.accounts.models import User
from apps.orders.models import Order
from apps.payments import services
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff():
    return User.objects.create_user("09129990200", password="x", is_staff=True)


@pytest.fixture
def paid(placed_order):
    return Payment.objects.create(
        order=placed_order, gateway_code="fake", amount=placed_order.payable, status=Payment.VERIFIED
    )


def test_refund_on_a_cancelled_order_closes_the_payment_and_the_order_once(placed_order, paid, staff):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.CANCELLED)

    result = services.record_refund(paid.pk, by=staff, note="پیگیری ۱۲۳")

    placed_order.refresh_from_db()
    assert (result.order_refunded, placed_order.status) == (True, Order.REFUNDED)
    assert Payment.objects.get(pk=paid.pk).status == Payment.REFUNDED
    assert placed_order.status_logs.filter(to_status=Order.REFUNDED, by_user=staff).count() == 1
    with pytest.raises(services.RefundError):  # a second click must not refund again
        services.record_refund(paid.pk, by=staff, note="دوباره")


def test_refund_is_refused_without_a_note_and_for_an_order_still_in_progress(placed_order, paid, staff):
    with pytest.raises(services.RefundError):
        services.record_refund(paid.pk, by=staff, note="  ")
    with pytest.raises(services.RefundError):  # the order is still pending_payment
        services.record_refund(paid.pk, by=staff, note="x")
    assert Payment.objects.get(pk=paid.pk).status == Payment.VERIFIED


def test_a_second_verified_payment_is_refunded_without_touching_the_order(placed_order, paid, staff):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.PAID)
    duplicate = Payment.objects.create(order=placed_order, gateway_code="fake", amount=1, status=Payment.VERIFIED)
    assert list(services.refund_candidates()) == [duplicate]

    result = services.record_refund(duplicate.pk, by=staff, note="تکراری")

    placed_order.refresh_from_db()
    assert (result.order_refunded, placed_order.status) == (False, Order.PAID)
    Payment.objects.filter(pk=paid.pk).update(status=Payment.REFUNDED)  # the first one is refunded elsewhere
    other = Payment.objects.create(order=placed_order, gateway_code="fake", amount=1, status=Payment.VERIFIED)
    assert other in services.refund_candidates()  # a refunded payment still makes the next one a duplicate
