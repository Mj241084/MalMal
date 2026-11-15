import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core.testing import find_ascii_digits
from apps.notifications.models import SmsLog
from apps.orders import workflow
from apps.orders.models import Order
from apps.payments import services as payment_services
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def test_pay_then_ship_then_invoice(client, buyer, placed_order, django_capture_on_commit_callbacks):
    client.force_login(buyer)
    invoice_url = reverse("orders:invoice", args=[placed_order.number])
    assert client.get(invoice_url).status_code == 404  # unpaid orders have no invoice

    payment_services.start(placed_order, "fake")
    authority = Payment.objects.get(order=placed_order).authority
    with django_capture_on_commit_callbacks(execute=True):
        client.get(reverse("payments:callback", args=["fake"]), {"Authority": authority, "Status": "OK"})
    assert Order.objects.get(pk=placed_order.pk).status == Order.PAID

    invoice = client.get(invoice_url)
    assert invoice.status_code == 200
    # D30: only Latin tokens (order number, ref id) may carry ASCII digits on screen.
    text, _inputs = find_ascii_digits(invoice.content.decode())
    assert not text, f"ASCII digits shown on the invoice: {text}"

    staff = User.objects.create_user("09129990002", password="x", is_staff=True)
    with django_capture_on_commit_callbacks(execute=True):
        workflow.change_status(placed_order.pk, Order.PROCESSING, by=staff)
        workflow.change_status(placed_order.pk, Order.SHIPPED, by=staff, tracking_code="123456789012345")
    assert set(SmsLog.objects.values_list("kind", flat=True)) == {"order_paid", "order_shipped"}

    client.force_login(User.objects.create_user("09129990003"))
    assert client.get(invoice_url).status_code == 404  # someone else's order
