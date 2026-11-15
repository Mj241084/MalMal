from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.engagement import counters
from apps.engagement.models import Like, ProductDailyStat, Review

pytestmark = pytest.mark.django_db


def test_reconcile_repairs_drift_and_a_second_run_changes_nothing(buyer, product):
    stranger = User.objects.create_user("09125550002")
    Like.objects.create(user=buyer, product=product)
    Review.objects.create(user=buyer, product=product, rating=5, body="متن", status=Review.APPROVED)
    Review.objects.create(user=stranger, product=product, rating=2, body="متن", status=Review.PENDING)
    Product.objects.filter(pk=product.pk).update(like_count=40, review_count=9, rating_sum=1, rating_avg=Decimal("3.3"))

    assert counters.reconcile() == 1

    stats = Product.objects.get(pk=product.pk)
    assert (stats.like_count, stats.review_count, stats.rating_sum, stats.rating_avg) == (1, 1, 5, Decimal("5.0"))
    assert counters.reconcile() == 0


def test_deleting_a_user_takes_their_likes_out_of_the_counter(buyer, product):
    Like.objects.create(user=buyer, product=product)
    assert Product.objects.get(pk=product.pk).like_count == 1

    buyer.delete()  # cascade: the post_delete signal still fires for every Like

    assert Product.objects.get(pk=product.pk).like_count == 0


def test_purchases_accumulate_in_one_ledger_row_and_invalidate_nothing(product):
    rev = Product.objects.get(pk=product.pk).rev

    counters.add_purchases({product.pk: 2})
    counters.add_purchases({product.pk: 3})

    stats = Product.objects.get(pk=product.pk)
    assert ProductDailyStat.objects.get(product=product).purchases == 5
    assert (stats.purchase_count_total, stats.purchase_count_30d, stats.rev) == (5, 5, rev)


def test_recount_uses_only_the_last_30_days_and_trims_the_ledger(product):
    today = timezone.localdate()
    for days_ago, qty in ((0, 2), (29, 3), (30, 7), (120, 4)):
        ProductDailyStat.objects.create(product=product, date=today - timedelta(days=days_ago), purchases=qty)
    Product.objects.filter(pk=product.pk).update(purchase_count_30d=99)

    assert counters.recount_purchases(today) == 1
    assert Product.objects.get(pk=product.pk).purchase_count_30d == 5
    assert counters.recount_purchases(today) == 0
    assert ProductDailyStat.objects.count() == 3  # the 120-day-old row is gone, day 30 is kept for the ledger
