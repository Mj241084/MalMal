from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.cart.models import CartItem
from apps.catalog.models import Product, Variant
from apps.engagement.models import ProductDailyStat
from apps.notifications.models import SmsLog
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments import gateways
from apps.payments import services as payment_services
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def payment(placed_order) -> Payment:
    payment_services.start(placed_order, "fake")
    return Payment.objects.get(order=placed_order)


def _callback(client, authority, ok=True):
    return client.get(
        reverse("payments:callback", args=["fake"]),
        {"Authority": authority, "Status": "OK" if ok else "NOK"},
    )


def _expire(order):
    Order.objects.filter(pk=order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))
    assert order_services.expire_order(order.pk)


def test_repeated_callback_pays_the_order_once(
    client, buyer, payment, placed_order, product, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        for _ in range(3):
            _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.PAID
    assert Payment.objects.filter(status=Payment.VERIFIED).count() == 1
    assert SmsLog.objects.filter(kind="order_paid").count() == 1
    assert Product.objects.get(pk=product.pk).purchase_count_total == 2
    assert ProductDailyStat.objects.get(product=product).purchases == 2
    assert not CartItem.objects.filter(cart__user=buyer).exists()


def test_failed_verification_keeps_the_order_pending_and_reserved(client, payment, placed_order, product, monkeypatch):
    monkeypatch.setattr(gateways.FakeGateway, "verify", lambda self, **kwargs: gateways.VerifyResult(False))

    _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.PENDING
    assert Payment.objects.get(pk=payment.pk).status == Payment.FAILED
    assert Variant.objects.get(pk=product.variants.get().pk).stock == 3
    assert not SmsLog.objects.exists()


def test_cancelled_payment_can_be_retried_within_the_reservation(client, payment, placed_order):
    _callback(client, payment.authority, ok=False)

    placed_order.refresh_from_db()
    assert Payment.objects.get(pk=payment.pk).status == Payment.CANCELLED
    assert placed_order.status == Order.PENDING and placed_order.can_pay_now


def test_payment_after_expiry_takes_the_stock_back(client, payment, placed_order, product):
    _expire(placed_order)
    assert Variant.objects.get(pk=product.variants.get().pk).stock == 5

    _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.PAID
    assert Variant.objects.get(pk=product.variants.get().pk).stock == 3


def test_payment_after_expiry_without_stock_is_recorded_not_lost(client, payment, placed_order, product):
    _expire(placed_order)
    Variant.objects.filter(pk=product.variants.get().pk).update(stock=1)  # someone else bought it meanwhile

    _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.EXPIRED  # a human refunds; the verified payment stays on record
    assert Payment.objects.get(pk=payment.pk).status == Payment.VERIFIED


def test_expiry_skips_an_order_whose_payment_is_being_verified(payment, placed_order):
    Payment.objects.filter(pk=payment.pk).update(status=Payment.VERIFYING)
    Order.objects.filter(pk=placed_order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))

    assert order_services.expire_order(placed_order.pk) is False


def test_dev_gateway_is_hidden_outside_debug(client, checkout_env, settings):
    settings.DEBUG = False

    assert "fake" not in [g.code for g in gateways.available()]
    assert client.get(reverse("payments:fake_bank", args=["FAKE1"])).status_code == 404


def test_zarinpal_sends_rials_and_accepts_an_already_verified_payment(monkeypatch, settings):
    settings.ZARINPAL_SANDBOX = True
    settings.ZARINPAL_MERCHANT_ID = ""
    sent = []

    def fake_post(self, path, body):
        sent.append((path, body))
        if path == "request":
            return {"data": {"code": 100, "authority": "S000"}, "errors": []}
        return {"data": {"code": 101, "ref_id": 7, "card_pan": "502229******5995"}, "errors": []}

    monkeypatch.setattr(gateways.ZarinpalGateway, "_post", fake_post)
    gateway = gateways.ZarinpalGateway()

    started = gateway.request(
        amount=46_800_000,
        callback_url="http://x/cb",
        description="d",
        mobile="09121234567",
        order_number="ML-1",
    )
    verified = gateway.verify(authority="S000", amount=46_800_000)

    assert sent[0][1]["amount"] == 468_000_000 and sent[0][1]["currency"] == "IRR"
    assert started.redirect_url == "https://sandbox.zarinpal.com/pg/StartPay/S000"
    assert verified.ok and sent[1][1]["amount"] == 468_000_000


def test_verified_payment_on_a_dead_order_is_flagged_for_refund(placed_order):
    payment = Payment.objects.create(order=placed_order, gateway_code="fake", amount=1, status=Payment.VERIFIED)
    assert not payment_services.refund_candidates().exists()

    Order.objects.filter(pk=placed_order.pk).update(status=Order.EXPIRED)

    assert list(payment_services.refund_candidates()) == [payment]
