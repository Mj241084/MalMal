"""Manual stock changes (D43): ledger, no negative stock, compare-and-set, real restock only."""

import pytest
from django.db import transaction

from apps.catalog import stock
from apps.catalog.models import StockMovement
from apps.engagement.models import StockSubscription

pytestmark = pytest.mark.django_db


def test_change_is_logged_and_refreshes_the_product(product, django_capture_on_commit_callbacks):
    variant = product.variants.get()
    with django_capture_on_commit_callbacks(execute=True), transaction.atomic():
        stock.adjust_manual(variant.pk, -5, note="شمارش")

    variant.refresh_from_db()
    product.refresh_from_db()
    assert variant.stock == 0 and product.in_stock is False
    movement = StockMovement.objects.get(variant=variant)
    assert (movement.delta, movement.reason, movement.note) == (-5, StockMovement.REASON_MANUAL, "شمارش")


def test_never_goes_negative_and_expected_stock_is_checked(product):
    variant = product.variants.get()
    with pytest.raises(stock.StockConflict):
        stock.adjust_manual(variant.pk, -6, note="x")
    with pytest.raises(stock.StockConflict) as caught:
        stock.adjust_manual(variant.pk, 1, note="x", expected_stock=4)
    assert caught.value.current == 5
    assert not StockMovement.objects.exists()


def test_subscribers_are_marked_only_when_stock_leaves_zero(buyer, product, django_capture_on_commit_callbacks):
    variant = product.variants.get()
    sub = StockSubscription.objects.create(user=buyer, variant=variant)

    def move(delta):
        with django_capture_on_commit_callbacks(execute=True), transaction.atomic():
            stock.adjust_manual(variant.pk, delta, note="x")

    move(2)  # 5 -> 7: not a restock
    assert StockSubscription.objects.get(pk=sub.pk).restocked_at is None
    move(-7)  # -> 0
    move(4)  # 0 -> 4: a real restock
    assert StockSubscription.objects.get(pk=sub.pk).restocked_at is not None
