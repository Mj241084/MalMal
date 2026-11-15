"""Template context processors for shared shell data."""

from __future__ import annotations

from django.conf import settings

from apps.core.models import FooterLink, SiteSettings


def site_context(request) -> dict:
    from apps.cart.services import count as cart_count
    from apps.catalog.menu import featured_categories, menu_categories

    return {
        "site_settings": SiteSettings.get_solo(),
        "footer_link_groups": FooterLink.get_grouped(),
        "site_url": settings.SITE_URL,
        "nav_categories": menu_categories(),
        "nav_featured": featured_categories(),
        "cart_count": cart_count(getattr(request, "user", None)),
    }
