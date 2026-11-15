"""Shipping method resolution shared by the product page, cart and checkout."""

from __future__ import annotations

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod


def default_method() -> ShippingMethod | None:
    return ShippingMethod.objects.filter(is_active=True).order_by("sort", "pk").first()


def product_page_note() -> str:
    method = default_method()
    return method.product_note if method and method.product_note else SiteSettings.get_solo().shipping_note
