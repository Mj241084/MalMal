"""Redis-backed rate limiting for sensitive actions (docs/02 §4)."""

from __future__ import annotations

import contextlib

from django.core.cache import caches

CACHE_ALIAS = "ratelimit"


def _cache():
    return caches[CACHE_ALIAS]


def consume(key: str, limit: int, window_seconds: int) -> bool:
    """Count one hit for `key`; return False when the limit is exceeded."""
    cache = _cache()
    try:
        cache.add(key, 0, window_seconds)
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window_seconds)
        count = 1
    return count <= limit


def refund(key: str) -> None:
    """Give back a consumed hit (used when the action itself failed)."""
    with contextlib.suppress(ValueError, NotImplementedError):
        _cache().decr(key)


def otp_keys(mobile: str, ip: str | None) -> tuple[str, str, str | None]:
    mobile_key_h = f"otp:mobile:{mobile}:h"
    mobile_key_d = f"otp:mobile:{mobile}:d"
    ip_key_h = f"otp:ip:{ip}:h" if ip else None
    return mobile_key_h, mobile_key_d, ip_key_h


MOBILE_HOURLY_LIMIT = 5
MOBILE_DAILY_LIMIT = 10
IP_HOURLY_LIMIT = 20
HOUR = 60 * 60
DAY = 60 * 60 * 24
