"""Cached trust items with their own revision counter.

The counter is part of the product-detail cache key, so editing a trust item in
the admin invalidates the rendered product pages immediately instead of waiting
for the 12h TTL.
"""

from __future__ import annotations

from apps.core.cache import get_or_build, read_epoch, safe_cache_incr_epoch

TRUST_REV_KEY = "trust_rev"
TRUST_TTL = 60 * 60 * 24
TRUST_LIMIT = 3


def trust_revision() -> int:
    return read_epoch(TRUST_REV_KEY)


def bump_trust_revision() -> None:
    safe_cache_incr_epoch(TRUST_REV_KEY)


def _build(limit: int) -> list[dict]:
    from apps.marketing.models import TrustItem

    return [
        {
            "icon": item.icon,
            "title": item.title,
            "subtitle": item.subtitle,
            "is_placeholder": item.is_placeholder,
        }
        for item in TrustItem.objects.filter(is_active=True).order_by("sort", "pk")[:limit]
    ]


def trust_items(limit: int = TRUST_LIMIT) -> list[dict]:
    return get_or_build(f"trust:{trust_revision()}:{limit}", lambda: _build(limit), TRUST_TTL)
