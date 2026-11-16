"""The door: a forgotten decorator is the one panel bug that must never reach production."""

import pytest
from django.urls import reverse

from apps.orders.models import Order
from apps.panel import urls

pytestmark = pytest.mark.django_db


def test_every_panel_view_declares_its_access_rule():
    missing = [str(p.pattern) for p in urls.urlpatterns if not hasattr(p.callback, "panel_rule")]
    assert not missing, f"Add @panel_view(...) or @public_view: {missing}"


@pytest.mark.parametrize(
    ("name", "args"),
    [("panel:orders", []), ("panel:payments", []), ("panel:order_detail", ["ML-00000001"])],
)
def test_anonymous_goes_to_login_and_staff_without_the_permission_gets_403(client, staff_client, name, args):
    url = reverse(name, args=args)

    assert client.get(url)["Location"].startswith(reverse("panel:login"))
    assert staff_client("accounts.view_user").get(url).status_code == 403


def test_status_changes_need_the_manage_permission_and_go_through_the_workflow(staff_client, placed_order):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.PAID)  # tests may; the architecture scan skips them
    url = reverse("panel:order_status", args=[placed_order.number])

    viewer = staff_client("orders.view_order", mobile="09129990101")
    assert viewer.post(url, {"to": Order.PROCESSING}).status_code == 403

    manager = staff_client("orders.view_order", "orders.manage_order_status", mobile="09129990102")
    manager.post(url, {"to": Order.CANCELLED})  # no reason: refused
    placed_order.refresh_from_db()
    assert placed_order.status == Order.PAID

    manager.post(url, {"to": Order.CANCELLED, "note": "درخواست مشتری"})
    placed_order.refresh_from_db()
    assert placed_order.status == Order.CANCELLED
    assert placed_order.status_logs.get(to_status=Order.CANCELLED).by_user.mobile == "09129990102"
