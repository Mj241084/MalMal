from types import SimpleNamespace

import pytest

from apps.engagement import social


@pytest.mark.parametrize(
    ("likes", "liked", "expected"),
    [
        (4, False, []),
        (5, False, ["۵ نفر این محصول را پسندیده‌اند"]),
        (1200, False, ["۱٫۲ هزار نفر این محصول را پسندیده‌اند"]),
        (0, True, ["شما این محصول را پسندیده‌اید"]),
        (1, True, ["شما این محصول را پسندیده‌اید"]),
        (2, True, ["شما و ۱ نفر دیگر این محصول را پسندیده‌اید"]),
    ],
)
def test_like_line(likes, liked, expected):
    product = SimpleNamespace(like_count=likes, purchase_count_30d=0)
    assert social.product_lines(product, liked=liked) == expected


@pytest.mark.parametrize(
    ("purchases", "expected"),
    [
        (4, []),
        (5, ["۵ نفر در ۳۰ روز گذشته این محصول را خریده‌اند"]),
        (12_000, ["۱۲ هزار نفر در ۳۰ روز گذشته این محصول را خریده‌اند"]),
    ],
)
def test_purchase_line(purchases, expected):
    product = SimpleNamespace(like_count=0, purchase_count_30d=purchases)
    assert social.product_lines(product, liked=False) == expected


@pytest.mark.parametrize(
    ("stock", "expected"),
    [(0, ""), (3, "تنها ۳ عدد در انبار باقی مانده"), (5, "تنها ۵ عدد در انبار باقی مانده"), (6, "")],
)
def test_low_stock_line(stock, expected):
    assert social.low_stock_line(SimpleNamespace(stock=stock), 5) == expected


@pytest.mark.parametrize(
    ("number", "expected"),
    [(999, "۹۹۹"), (1000, "۱ هزار"), (1999, "۱٫۹ هزار"), (2_500_000, "۲٫۵ میلیون")],
)
def test_counts_are_truncated_never_rounded_up(number, expected):
    assert social.compact_count(number) == expected
