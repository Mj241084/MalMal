import pytest
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Product
from apps.engagement import services
from apps.engagement.models import Review
from apps.orders.models import Order

pytestmark = pytest.mark.django_db

TEXT = "کیفیت ساخت عالی است و به‌خوبی کار می‌کند"


def _post(client, product, **data):
    payload = {"rating": "4", "body": TEXT, **data}
    return client.post(reverse("engagement:reviews", args=[product.pk]), payload, HTTP_HX_REQUEST="true")


def _public(product) -> str:
    return Client().get(reverse("engagement:reviews", args=[product.pk]), HTTP_HX_REQUEST="true").content.decode()


def test_only_approved_reviews_are_public_and_counted(client, buyer, product):
    client.force_login(buyer)
    _post(client, product)
    review = Review.objects.get()
    assert review.status == Review.PENDING
    assert "کیفیت ساخت" not in _public(product)
    assert Product.objects.get(pk=product.pk).review_count == 0

    services.moderate(review, Review.APPROVED)
    stats = Product.objects.values_list("review_count", "rating_sum", "rating_avg").get(pk=product.pk)
    assert (stats[0], stats[1], float(stats[2])) == (1, 4, 4.0)
    assert "کیفیت ساخت" in _public(product)

    _post(client, product, rating="2")  # editing sends it back to the queue and out of the counters
    review.refresh_from_db()
    assert (review.status, review.rating) == (Review.PENDING, 2)
    assert Product.objects.get(pk=product.pk).review_count == 0
    assert "کیفیت ساخت" not in _public(product)


def test_review_text_is_escaped(client, buyer, product):
    client.force_login(buyer)
    _post(client, product, body="<script>alert(1)</script> متن آزمایشی")
    services.moderate(Review.objects.get(), Review.APPROVED)

    body = _public(product)
    assert "<script>alert" not in body
    assert "&lt;script&gt;" in body


def test_verified_buyer_needs_a_paid_order(client, buyer, placed_order, product):
    client.force_login(buyer)
    _post(client, product)
    assert Review.objects.get().is_verified_buyer is False  # the order is still pending payment

    Order.objects.filter(pk=placed_order.pk).update(status=Order.PAID)
    _post(client, product)
    assert Review.objects.get().is_verified_buyer is True


def test_sixth_submission_in_an_hour_is_refused(client, buyer, product):
    client.force_login(buyer)
    for n in range(1, 7):
        _post(client, product, body=f"{TEXT} {n}")

    assert Review.objects.get().body.endswith(" 5")


def test_product_page_etag_moves_when_a_review_is_approved(buyer, product):
    url = product.get_absolute_url()
    before = Client().get(url)["ETag"]

    review = services.submit_review(buyer, product, rating=5, body=TEXT)
    assert Client().get(url)["ETag"] == before  # a pending review changes nothing public

    services.moderate(review, Review.APPROVED)
    response = Client().get(url, HTTP_IF_NONE_MATCH=before)
    assert response.status_code == 200 and response["ETag"] != before
