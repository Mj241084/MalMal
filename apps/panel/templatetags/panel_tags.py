from __future__ import annotations

from django import template

from apps.panel import nav

register = template.Library()


@register.inclusion_tag("panel/partials/sidebar.html", takes_context=True)
def render_sidebar(context):
    request = context.get("request")
    user = getattr(request, "user", None)
    return {
        "groups": nav.visible_groups(user, request.path) if user else [],
    }


@register.inclusion_tag("panel/partials/badge.html")
def render_badge(key: str, counts: dict[str, int]):
    count = counts.get(key, 0)
    return {"key": key, "count": count, "visible": count > 0}
