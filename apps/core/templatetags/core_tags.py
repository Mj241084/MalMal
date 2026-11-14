"""Shared core template tags and filters (icons, currency, digits)."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from apps.core.jalali import to_fa_digits
from apps.core.models import SiteSettings, StaticPage
from apps.core.text import format_toman, to_fa_text

logger = logging.getLogger(__name__)
register = template.Library()

_SPRITE_CACHE: dict[str, tuple[float, frozenset[str]]] = {}


def _load_sprite_ids(path: Path) -> frozenset[str]:
    if not path.is_file():
        return frozenset()
    mtime = path.stat().st_mtime
    cached = _SPRITE_CACHE.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    tree = ET.parse(path)
    root = tree.getroot()
    ids = frozenset(elem.attrib["id"] for elem in root if elem.tag.split("}")[-1] == "symbol" and "id" in elem.attrib)
    _SPRITE_CACHE[str(path)] = (mtime, ids)
    return ids


def _icon_exists(name: str) -> bool:
    base_dir = Path(settings.BASE_DIR)
    built_sprite = base_dir / "static" / "sprite.svg"
    if built_sprite.is_file():
        return name in _load_sprite_ids(built_sprite)
    src_sprite = base_dir / "static" / "src" / "sprite.svg"
    return name in _load_sprite_ids(src_sprite)


@register.filter
def toman(value) -> str:
    """Format an integer amount in Tomans with Persian digits and U+066C separator."""
    return format_toman(value)


@register.filter(name="fa_digits")
def fa_digits_filter(value) -> str:
    """Convert ASCII digits to Persian digits."""
    return to_fa_digits(value)


@register.filter(name="fa_text")
def fa_text_filter(value) -> str:
    """Persian digits for names, addresses and titles (Latin codes inside are preserved)."""
    return to_fa_text(value)


@register.simple_tag
def static_page_url(slug: str) -> str:
    """URL of an active static page, or '' so templates can hide links to pages that do not exist yet."""
    if StaticPage.objects.filter(slug=slug, is_active=True).exists():
        return reverse("core:static_page", args=[slug])
    return ""


@register.simple_tag
def icon(name: str, size: int = 18, flip: bool = False, safe: bool = False, **kwargs) -> str:
    """Render an SVG icon from static/sprite.svg with 1.5 stroke and optional RTL flip.

    ``safe=True`` is for icon names that come from the database (e.g. TrustItem.icon):
    an unknown name renders nothing instead of raising, so a typo in the admin cannot
    take a page down in DEBUG.
    """
    if not _icon_exists(name):
        if settings.DEBUG and not safe:
            raise ValueError(
                f"Icon '{name}' not found in static/sprite.svg. Run `uv run python scripts/build_sprite.py`."
            )
        logger.warning("Missing icon '%s' requested in template.", name)
        return ""

    extra_class = kwargs.pop("class", "") or kwargs.pop("css_class", "")
    classes = ["shrink-0"]
    if flip:
        classes.append("rtl:-scale-x-100")
    if extra_class:
        classes.append(str(extra_class))

    sprite_href = f"{static('sprite.svg')}#{name}"
    return format_html(
        '<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
        'stroke-linejoin="round" class="{classes}" aria-hidden="true">'
        '<use href="{href}"></use></svg>',
        size=int(size),
        classes=" ".join(classes),
        href=sprite_href,
    )


@register.simple_tag(takes_context=True)
def brand_name(context, **kwargs) -> str:
    """Render display brand name in Dastnevis, splitting ZWNJ into safe spans (font lacks U+200C)."""
    site_settings = context.get("site_settings")
    name = getattr(site_settings, "store_name", "") or SiteSettings.get_solo().store_name or "مل‌مل"
    extra_class = kwargs.pop("class", "") or kwargs.pop("css_class", "")
    classes = f"font-brand {extra_class}".strip()

    if "‌" in name:
        segments = [seg for seg in name.split("‌") if seg]
        inner = format_html_join("", '<span class="font-brand-seg">{}</span>', ((seg,) for seg in segments))
        return format_html('<span class="{classes}">{inner}</span>', classes=classes, inner=inner)
    return format_html('<span class="{classes}">{name}</span>', classes=classes, name=name)
