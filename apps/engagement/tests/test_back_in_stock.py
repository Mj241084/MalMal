from datetime import datetime

import pytest
from django.utils import timezone

from apps.catalog import stock
from apps.catalog.models import StockMovement, Variant
from apps.engagement import back_in_stock
from apps.notifications.models import SmsLog

pytestmark = pytest.mark.django_db
NOON = lambda: timezone.make_aware(datetime(2026, 11, 15, 12, 0))  # noqa: E731
NIGHT = lambda: timezone.make_aware(datetime(2026, 11, 15, 23, 0))  # noqa: E731


@pytest.fixture
def waiting(buyer, product):
    variant = product.variants.get()
    Variant.objects.filter(pk=variant.pk).update(stock=0)
    variant.refresh_from_db()
    back_in_stock.subscribe(buyer, variant.pk)
    return variant


def _restock(variant, capture):
    variant.stock = 4
    with capture(execute=True):
        variant.save()


def test_a_real_restock_sends_once_and_only_inside_the_allowed_hours(waiting, django_capture_on_commit_callbacks):
    _restock(waiting, django_capture_on_commit_callbacks)

    assert back_in_stock.send_due(NIGHT()) == 0  # held until morning, not lost
    assert back_in_stock.send_due(NOON()) == 1
    assert back_in_stock.send_due(NOON()) == 0
    assert SmsLog.objects.filter(kind="back_in_stock").count() == 1


def test_returning_a_reservation_does_not_notify(waiting):
    stock.increment(waiting.pk, 1, reason=StockMovement.REASON_EXPIRE)

    assert back_in_stock.send_due(NOON()) == 0
    assert not SmsLog.objects.exists()
