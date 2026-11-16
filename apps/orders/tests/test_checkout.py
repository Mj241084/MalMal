import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart import services as cart_services
from apps.catalog.models import StockMovement, Variant
from apps.core.testing import find_ascii_digits
from apps.orders import services
from apps.orders.models import Order

pytestmark = pytest.mark.django_db


def _fingerprint(user) -> str:
    lines, _ = cart_services.normalize(cart_services.get_cart(user))
    return cart_services.fingerprint(lines)


def _place(user, address, method, fingerprint=None):
    return services.place_order(
        user=user,
        address=address,
        method=method,
        buyer_form=None,
        seen_fingerprint=fingerprint or _fingerprint(user),
    )


def test_order_reserves_stock_and_is_a_snapshot(placed_order, product):
    variant = Variant.objects.get(pk=product.variants.get().pk)
    assert variant.stock == 3
    assert StockMovement.objects.get(variant=variant).delta == -2
    assert (placed_order.payable, placed_order.shipping_cost) == (2 * 46_800_000, 0)
    assert placed_order.shipping_payment_mode == "collect"

    variant.price = 1
    variant.save()
    product.title = "عنوان دیگر"
    product.save()
    item = placed_order.items.get()
    assert (item.unit_price, item.product_title) == (46_800_000, "ماشین لباسشویی بوش مدل WM-1234")


def test_changed_price_blocks_the_order(buyer, address, cart_item, checkout_env):
    seen = _fingerprint(buyer)
    cart_item.price += 1
    cart_item.save()

    with pytest.raises(services.CheckoutError) as exc:
        _place(buyer, address, checkout_env, seen)

    assert exc.value.changed
    assert not Order.objects.exists()
    assert Variant.objects.get(pk=cart_item.pk).stock == 5


def test_checkout_never_overwrites_a_filled_profile(client, buyer, address, cart_item, checkout_env):
    client.force_login(buyer)

    response = client.post(
        reverse("orders:place"),
        {
            "address_id": address.pk,
            "gateway": "fake",
            "fingerprint": _fingerprint(buyer),
            "first_name": "دیگری",
            "national_code": "1234567891",
            "national_code_confirm": "on",
        },
    )

    buyer.refresh_from_db()
    assert response.status_code == 302
    assert (buyer.first_name, buyer.national_code) == ("مریم", "0012345679")


def test_new_checkout_cancels_the_previous_pending_order(buyer, address, placed_order, checkout_env):
    variant = placed_order.items.get().variant
    cart_services.set_quantity(buyer, variant.pk, 1)

    _place(buyer, address, checkout_env)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.CANCELLED
    assert Variant.objects.get(pk=variant.pk).stock == 4  # first reservation returned, second taken


def test_expiry_returns_stock_exactly_once(placed_order):
    Order.objects.filter(pk=placed_order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))
    variant = placed_order.items.get().variant

    assert services.expire_order(placed_order.pk) is True
    assert services.expire_order(placed_order.pk) is False

    assert Variant.objects.get(pk=variant.pk).stock == 5
    assert Order.objects.get(pk=placed_order.pk).status == Order.EXPIRED


@pytest.mark.django_db(transaction=True)
def test_last_unit_goes_to_exactly_one_buyer(product, province, city, checkout_env):
    variant = product.variants.get()
    Variant.objects.filter(pk=variant.pk).update(stock=1)
    buyers = []
    for mobile in ("09121230011", "09121230012"):
        user = User.objects.create_user(mobile, first_name="الف", last_name="ب", national_code="0012345679")
        address = Address.objects.create(
            user=user,
            recipient_name="الف",
            recipient_mobile=mobile,
            province=province,
            city=city,
            address_text="خیابان",
            plate="1",
            postal_code="1234567890",
            is_default=True,
        )
        cart_services.set_quantity(user, variant.pk, 1)
        buyers.append((user, address, _fingerprint(user)))

    results, barrier = [], threading.Barrier(2)

    def attempt(user, address, fingerprint):
        try:
            barrier.wait()
            results.append(_place(user, address, checkout_env, fingerprint).pk)
        except services.CheckoutError:
            results.append(None)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt, args=args) for args in buyers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len([r for r in results if r]) == 1
    assert Order.objects.count() == 1
    assert Variant.objects.get(pk=variant.pk).stock == 0


def test_cart_checkout_and_order_pages_show_persian_digits(client, buyer, placed_order):
    client.force_login(buyer)
    urls = [
        reverse("cart:detail"),
        reverse("orders:checkout"),
        reverse("orders:list"),
        reverse("orders:detail", args=[placed_order.number]),
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, url
        text, inputs = find_ascii_digits(response.content.decode())
        assert not text, f"ASCII digits on {url}: {text}"
        assert not inputs, f"ASCII digit inputs on {url}: {inputs}"
