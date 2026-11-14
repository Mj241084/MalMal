"""Template context processors for shared shell data."""

from __future__ import annotations

from django.conf import settings

from apps.core.models import FooterLink, SiteSettings


def site_context(request) -> dict:
    from apps.catalog.menu import featured_categories, menu_categories

    return {
        "site_settings": SiteSettings.get_solo(),
        "footer_link_groups": FooterLink.get_grouped(),
        "site_url": settings.SITE_URL,
        "nav_categories": menu_categories(),
        "nav_featured": featured_categories(),
        # Cart lands in P3; the badge stays in the DOM so layout never shifts.
        "cart_count": 0,
    }
