from datetime import date

import pytest

from apps.orders.models import Order
from apps.panel import queries

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@pytest.mark.django_db
def test_order_search_finds_by_number_and_by_persian_mobile_fragment(placed_order):
    for text in (placed_order.number.lower(), placed_order.buyer_mobile[-6:].translate(FA)):
        assert Order.objects.filter(queries.order_search_q(text), pk=placed_order.pk).exists()


def test_the_end_day_of_a_range_is_included_and_a_reversed_range_is_swapped():
    low, high = queries.day_range("۱۴۰۵/۰۶/۳۰", "۱۴۰۵/۰۶/۲۹")  # 2026-09-21 and 2026-09-20

    assert (low.date(), high.date()) == (date(2026, 9, 20), date(2026, 9, 22))
