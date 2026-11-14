"""Cached navigation menu and featured categories for the real header."""

from __future__ import annotations

from django.urls import reverse

from apps.catalog.cache import get_or_build, menu_key
from apps.catalog.constants import TTL_MENU


def _to_dict(category) -> dict:
    return {
        "id": category.pk,
        "name": category.name,
        "url": reverse("catalog:category", args=[category.pk, category.slug]),
        "slug": category.slug,
    }


def _build_menu() -> dict:
    from apps.catalog.models import Category

    roots = list(
        Category.objects.filter(is_active=True, show_in_menu=True, parent__isnull=True).order_by("menu_order", "name")
    )
    children = list(
        Category.objects.filter(is_active=True, show_in_menu=True, parent__in=roots).order_by("menu_order", "name")
    )
    by_parent: dict[int, list[dict]] = {}
    for child in children:
        by_parent.setdefault(child.parent_id, []).append(_to_dict(child))

    featured = list(Category.objects.filter(is_active=True, is_featured=True).order_by("featured_order", "name")[:8])

    return {
        "menu": [{**_to_dict(root), "children": by_parent.get(root.pk, [])} for root in roots],
        "featured": [_to_dict(category) for category in featured],
    }


def navigation() -> dict:
    """Menu + featured categories, cached under the structural epoch."""
    return get_or_build(menu_key(), _build_menu, TTL_MENU)


def menu_categories() -> list[dict]:
    return navigation()["menu"]


def featured_categories() -> list[dict]:
    return navigation()["featured"]


def popular_categories(limit: int = 6) -> list[dict]:
    """Fallback suggestions when a search returns nothing."""
    from apps.catalog.models import Category

    categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by("menu_order", "name")[:limit]
    return [_to_dict(category) for category in categories]
