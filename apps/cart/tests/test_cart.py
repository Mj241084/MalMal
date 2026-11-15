import pytest

from apps.cart import services
from apps.cart.models import CartItem
from apps.catalog.models import Variant

pytestmark = pytest.mark.django_db


def test_quantity_is_clamped_to_max_orderable_and_zero_removes(buyer, product):
    variant = product.variants.get()
    Variant.objects.filter(pk=variant.pk).update(max_per_order=2)

    notice = services.set_quantity(buyer, variant.pk, 5)

    assert CartItem.objects.get(cart__user=buyer).qty == 2
    assert notice
    services.set_quantity(buyer, variant.pk, 0)
    assert not CartItem.objects.filter(cart__user=buyer).exists()


def test_merge_takes_the_max_never_the_sum_and_skips_unsellable(buyer, product):
    variant = product.variants.get()
    sold_out = Variant.objects.create(product=product, sku="WM-1234-B", title="مشکی", price=1_000, stock=0)
    services.set_quantity(buyer, variant.pk, 3)

    for _ in range(2):  # a repeated sync changes nothing
        services.merge_guest_items(buyer, [(variant.pk, 2), (sold_out.pk, 1)])
    assert dict(CartItem.objects.filter(cart__user=buyer).values_list("variant_id", "qty")) == {variant.pk: 3}

    services.merge_guest_items(buyer, [(variant.pk, 4)])
    assert CartItem.objects.get(cart__user=buyer).qty == 4
