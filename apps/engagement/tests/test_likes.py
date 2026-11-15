from urllib.parse import unquote

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.engagement import services
from apps.engagement.models import Like, Review

pytestmark = pytest.mark.django_db


def test_like_is_idempotent_and_the_counter_never_goes_negative(buyer, product):
    services.set_like(buyer, product.pk, True)
    services.set_like(buyer, product.pk, True)
    assert (Like.objects.count(), Product.objects.get(pk=product.pk).like_count) == (1, 1)

    services.set_like(buyer, product.pk, False)
    services.set_like(buyer, product.pk, False)
    assert (Like.objects.count(), Product.objects.get(pk=product.pk).like_count) == (0, 0)


def test_guests_are_sent_back_to_the_page_they_were_on(client, product):
    headers = {"HTTP_HX_REQUEST": "true", "HTTP_HX_CURRENT_URL": f"http://testserver{product.get_absolute_url()}"}
    attempts = (
        (reverse("engagement:like_set", args=[product.pk]), {"state": "1"}),
        (reverse("engagement:reviews", args=[product.pk]), {"rating": "5", "body": "متن آزمایشی کافی"}),
    )
    for url, data in attempts:
        response = client.post(url, data, **headers)
        redirect = unquote(response["HX-Redirect"])
        assert redirect.startswith(reverse("accounts:login") + "?next=")
        assert f"/p/{product.pk}/" in redirect
    assert not Like.objects.exists() and not Review.objects.exists()


def test_like_state_costs_the_same_for_one_card_or_twenty(client, buyer, product):
    ids = [product.pk]
    for index in range(19):
        extra = Product.objects.create(title=f"محصول {index}", category=product.category, status=Product.STATUS_ACTIVE)
        ids.append(extra.pk)
    for pk in ids:
        Like.objects.create(user=buyer, product_id=pk)
    client.force_login(buyer)
    url = reverse("engagement:like_state")

    def queries(subset):
        with CaptureQueriesContext(connection) as context:
            response = client.get(url, {"ids": ",".join(map(str, subset))}, HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        return len(context.captured_queries)

    queries(ids[:1])  # warm the shared caches (menu, settings)
    assert queries(ids[:1]) == queries(ids)


def test_wishlist_shows_only_my_active_products(client, buyer, product):
    hidden = Product.objects.create(title="پیش‌نویس مخفی", category=product.category, status=Product.STATUS_DRAFT)
    stranger = User.objects.create_user("09125550001")
    for user, item in ((buyer, product), (buyer, hidden), (stranger, product)):
        Like.objects.create(user=user, product=item)

    guest = client.get(reverse("engagement:wishlist"))
    assert guest.status_code == 302 and guest["Location"].startswith("/login/")

    client.force_login(buyer)
    body = client.get(reverse("engagement:wishlist")).content.decode()
    assert product.title in body and hidden.title not in body
