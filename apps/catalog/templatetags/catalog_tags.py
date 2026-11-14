"""Catalog template tags: product cards, rails, image srcset, query helpers."""

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def srcset(image) -> str:
    if not image:
        return ""
    return image.srcset()


@register.filter
def image_url(image) -> str:
    if not image:
        return ""
    return image.largest()


@register.inclusion_tag("partials/_product_card.html")
def product_card(product, priority=False) -> dict:
    return {"product": product, "priority": priority}


@register.inclusion_tag("partials/_product_rail.html")
def product_rail(title, products, view_all_url="", rail_id="rail") -> dict:
    return {"title": title, "products": products, "view_all_url": view_all_url, "rail_id": rail_id}


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs) -> str:
    """Rebuild the current querystring with some parameters replaced or removed."""
    request = context.get("request")
    if request is None:
        return ""
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.simple_tag(takes_context=True)
def query_has(context, key, value) -> bool:
    request = context.get("request")
    if request is None:
        return False
    return value in request.GET.getlist(key)


@register.filter
def get_item(mapping, key):
    if not mapping:
        return None
    return mapping.get(key)
