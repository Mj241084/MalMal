"""Stock change and review moderation through the panel: permission, ledger, counters, stale decisions."""

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import StockMovement
from apps.engagement.models import Review
from apps.panel import queries

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-12345"


def _staff(client, mobile, *codenames):
    user = User.objects.create_user(mobile, password=PASSWORD, is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    assert client.post(reverse("panel:login"), {"mobile": mobile, "password": PASSWORD}).status_code == 302
    return user


def test_stock_change_needs_adjust_permission_and_lands_in_the_ledger(client, product):
    variant = product.variants.get()
    url = reverse("panel:stock_adjust", args=[variant.pk])
    payload = {"mode": "set", "amount": "8", "expected": str(variant.stock), "reason": "شمارش انبار"}
    staff = _staff(client, "09121110001", "view_variant")

    assert client.post(url, payload).status_code == 403

    staff.user_permissions.add(Permission.objects.get(codename="adjust_stock"))
    client.post(url, payload)
    variant.refresh_from_db()
    assert variant.stock == 8
    movement = StockMovement.objects.get(variant=variant)
    assert (movement.delta, movement.reason) == (3, StockMovement.REASON_MANUAL)
    assert "شمارش انبار" in movement.note and staff.mobile in movement.note


def test_moderation_keeps_counters_right_and_refuses_stale_decisions(client, product, buyer):
    review = Review.objects.create(user=buyer, product=product, rating=4, body="کیفیت ساخت خوب است")
    _staff(client, "09121110002", "view_review", "change_review")
    decide = reverse("panel:review_decide")
    seen = f"{review.pk}:{queries.stamp(review.updated_at)}"

    client.post(decide, {"action": "approve", "review": seen})
    review.refresh_from_db()
    product.refresh_from_db()
    assert review.status == Review.APPROVED and product.review_count == 1

    client.post(decide, {"action": "reject", "review": seen, "reason": "x"})  # the version it saw is gone
    review.refresh_from_db()
    assert review.status == Review.APPROVED

    fresh = f"{review.pk}:{queries.stamp(review.updated_at)}"
    client.post(decide, {"action": "reject", "review": fresh, "reason": "نامناسب"})
    review.refresh_from_db()
    product.refresh_from_db()
    assert review.status == Review.REJECTED and review.rejection_reason == "نامناسب"
    assert product.review_count == 0

    client.post(reverse("panel:review_reply", args=[review.pk]), {"reply": "ممنون از نظر شما"})
    review.refresh_from_db()
    assert review.admin_reply == "ممنون از نظر شما" and review.status == Review.REJECTED
