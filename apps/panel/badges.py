"""Navigation counters."""

from __future__ import annotations

from collections.abc import Callable

from apps.core.cache import safe_cache_get, safe_cache_set
from apps.panel import nav

TTL = 30
BADGES: dict[str, Callable[[], int]] = {}


def register(key: str):
    def decorator(func: Callable[[], int]) -> Callable[[], int]:
        BADGES[key] = func
        return func

    return decorator


def counts_for(user) -> dict[str, int]:
    keys = {link.item.badge for _, links in nav.visible_groups(user, "") for link in links if link.item.badge}
    counts: dict[str, int] = {}
    for key in sorted(keys):
        func = BADGES.get(key)
        if func is None:
            continue
        cached = safe_cache_get(f"panel:badge:{key}")
        if not isinstance(cached, int):
            cached = int(func())
            safe_cache_set(f"panel:badge:{key}", cached, TTL)
        counts[key] = cached
    return counts
