import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Product, Variant
from apps.engagement import counters
from apps.notifications import sms
from apps.notifications.models import SmsLog
from apps.orders import workflow
from apps.orders.models import Order

pytestmark = pytest.mark.django_db
CODE = "123456789012345"


@pytest.fixture
def staff():
    return User.objects.create_user("09129990001", password="x", is_staff=True)


@pytest.fixture
def paid_order(placed_order):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.PAID, paid_at=timezone.now())
    counters.add_purchases({placed_order.items.get().product_id: 2})
    return placed_order


def test_only_listed_moves_are_allowed_and_each_is_logged(paid_order, staff):
    with pytest.raises(workflow.TransitionError):
        workflow.change_status(paid_order.pk, Order.DELIVERED, by=staff)

    workflow.change_status(paid_order.pk, Order.PROCESSING, by=staff)

    assert paid_order.status_logs.filter(to_status=Order.PROCESSING, by_user=staff).count() == 1


def test_shipping_needs_a_tracking_code_and_sends_the_sms(paid_order, staff, django_capture_on_commit_callbacks):
    workflow.change_status(paid_order.pk, Order.PROCESSING, by=staff)
    with pytest.raises(workflow.TransitionError):
        workflow.change_status(paid_order.pk, Order.SHIPPED, by=staff)

    with django_capture_on_commit_callbacks(execute=True):
        workflow.change_status(paid_order.pk, Order.SHIPPED, by=staff, tracking_code=CODE)

    assert Order.objects.get(pk=paid_order.pk).tracking_code == CODE
    assert SmsLog.objects.filter(kind="order_shipped").count() == 1


def test_cancelling_a_paid_order_returns_stock_and_purchases_exactly_once(paid_order, staff, product):
    variant = product.variants.get()
    assert Variant.objects.get(pk=variant.pk).stock == 3  # 5 minus the 2 reserved at checkout

    workflow.change_status(paid_order.pk, Order.CANCELLED, by=staff, note="لغو آزمایشی")
    with pytest.raises(workflow.TransitionError):  # a second cancel must not return stock again
        workflow.change_status(paid_order.pk, Order.CANCELLED, by=staff)

    stats = Product.objects.get(pk=product.pk)
    assert Variant.objects.get(pk=variant.pk).stock == 5
    assert (stats.purchase_count_total, stats.purchase_count_30d) == (0, 0)


def test_a_failing_sms_never_reverts_the_status(paid_order, staff, monkeypatch, django_capture_on_commit_callbacks):
    def boom(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(sms, "send_template", boom)
    workflow.change_status(paid_order.pk, Order.PROCESSING, by=staff)

    with django_capture_on_commit_callbacks(execute=True):
        workflow.change_status(paid_order.pk, Order.SHIPPED, by=staff, tracking_code=CODE)

    assert Order.objects.get(pk=paid_order.pk).status == Order.SHIPPED


def test_the_admin_status_endpoint_needs_the_manage_permission(client, paid_order, staff):
    client.force_login(staff)
    url = reverse("admin:orders_order_status", args=[paid_order.pk])

    assert client.get(url).status_code == 403

    staff.user_permissions.add(Permission.objects.get(codename="manage_order_status"))
    response = client.post(url, {"to_status": Order.PROCESSING})
    assert response.status_code == 302
    assert Order.objects.get(pk=paid_order.pk).status == Order.PROCESSING
