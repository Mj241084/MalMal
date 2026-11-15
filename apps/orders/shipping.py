"""Shipping method resolution shared by the product page, cart and checkout."""

from __future__ import annotations

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod

# Public tracking page per carrier (docs/vendors/tipax/08): the code is typed there,
# no deep link is documented, so we never build one.
TRACKING_PAGES = {"tipax": "https://tipaxco.com/tracking"}


def default_method() -> ShippingMethod | None:
    return ShippingMethod.objects.filter(is_active=True).order_by("sort", "pk").first()


def product_page_note() -> str:
    method = default_method()
    return method.product_note if method and method.product_note else SiteSettings.get_solo().shipping_note


def has_tracking(order) -> bool:
    method = order.shipping_method
    return method.has_tracking if method is not None else True  # deleted method: ask for a code, the safe default


def tracking_page(order) -> str:
    method = order.shipping_method
    return TRACKING_PAGES.get(method.code, "") if method is not None and order.tracking_code else ""
