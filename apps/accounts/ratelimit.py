"""Cache-backed rate limiting for sensitive actions (docs/02 §4).

`redis` and `locmem` have a native `incr` that keeps the key's TTL, so they use the atomic add/incr path.
`database` has no such primitive: Django's generic `incr` rewrites the key with the default 24h TTL and
would stretch the hourly and 15-minute windows, so that backend stores an explicit `(count, expires)` pair.
"""

from __future__ import annotations

import contextlib
import time

from django.conf import settings
from django.core.cache import caches

CACHE_ALIAS = "ratelimit"
_NATIVE_INCR = ("redis", "locmem")


def _cache():
    return caches[CACHE_ALIAS]


def consume(key: str, limit: int, window_seconds: int) -> bool:
    """Count one hit for `key`; return False when the limit is exceeded."""
    cache = _cache()
    if settings.CACHE_BACKEND in _NATIVE_INCR:
        try:
            cache.add(key, 0, window_seconds)
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, window_seconds)
            count = 1
        return count <= limit
    now = time.time()
    count, expires = cache.get(key) or (0, now + window_seconds)
    if expires <= now:
        count, expires = 0, now + window_seconds
    count += 1
    cache.set(key, (count, expires), max(1, int(expires - now) + 1))
    return count <= limit


def refund(key: str) -> None:
    """Give back a consumed hit (used when the action itself failed)."""
    cache = _cache()
    if settings.CACHE_BACKEND in _NATIVE_INCR:
        with contextlib.suppress(ValueError, NotImplementedError):
            cache.decr(key)
        return
    entry, now = cache.get(key), time.time()
    if entry and entry[1] > now and entry[0] > 0:
        cache.set(key, (entry[0] - 1, entry[1]), max(1, int(entry[1] - now) + 1))


def otp_keys(mobile: str) -> tuple[str, str]:
    return f"otp:mobile:{mobile}:h", f"otp:mobile:{mobile}:d"


MOBILE_HOURLY_LIMIT = 5
MOBILE_DAILY_LIMIT = 10
# One ceiling for the whole site. It replaces the per-IP limit (behind a CDN every visitor shares a few edge IPs)
# and only protects the SMS budget from someone cycling through many different numbers.
GLOBAL_KEY = "otp:global:h"
GLOBAL_HOURLY_LIMIT = 300
HOUR = 60 * 60
DAY = 60 * 60 * 24
