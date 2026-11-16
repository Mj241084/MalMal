"""Shipping helpers: the active method, page text, tracking, and what staff paste into the Tipax panel."""

from __future__ import annotations

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod

# [VERIFY] docs/vendors/neshan/: replace with a documented share link if there is one.
MAP_LINK = "https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"
# docs/vendors/tipax/08: only the public tracking page is documented; the customer types the code there.
TIPAX_TRACKING_PAGE = "https://tipaxco.com/tracking"


def default_method() -> ShippingMethod | None:
    """The method checkout uses: the first active one. None means shipping is off and checkout is blocked."""
    return ShippingMethod.objects.filter(is_active=True).order_by("sort", "pk").first()


def product_page_note() -> str:
    """Shipping line of the product page: the active method's text, with SiteSettings.shipping_note as fallback."""
    method = default_method()
    if method is not None and method.product_note:
        return method.product_note
    return SiteSettings.get_solo().shipping_note


def has_tracking(order) -> bool:
    """Whether this order's method issues a tracking code. A deleted method keeps the v1 default (Tipax: yes)."""
    method = order.shipping_method
    return True if method is None else method.has_tracking


def tracking_page(order) -> str:
    """Public tracking page to link next to the code; '' when there is no code or no known carrier page."""
    if not order.tracking_code:
        return ""
    method = order.shipping_method
    code = method.code if method is not None else ""
    if code == "tipax" or "تیپاکس" in (order.shipping_method_title or ""):
        return TIPAX_TRACKING_PAGE
    return ""


def recipient_text(order) -> str:
    """What staff paste into the Tipax panel: plain lines. ASCII digits on purpose (an outside system; D30 is for our screens)."""
    unit = f"، واحد {order.unit}" if order.unit else ""
    return "\n".join(
        [
            order.recipient_name,
            order.recipient_mobile,
            f"{order.province_name}، {order.city_name}",
            f"{order.address_text}، پلاک {order.plate}{unit}",
            f"کدپستی: {order.postal_code}",
        ]
    )


def map_link(order) -> str:
    if order.lat is None or order.lng is None:
        return ""
    return MAP_LINK.format(lat=f"{order.lat:.6f}", lng=f"{order.lng:.6f}")
