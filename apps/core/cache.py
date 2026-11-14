"""Redis cache key helpers and safe accessors."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

LOCK_TIMEOUT = 10
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_SECONDS = 0.02


def make_key(key: str, key_prefix: str, version: int) -> str:
    """Build cache key with project prefix directly: `mm:v1:<key>`."""
    return f"{key_prefix}:{key}"


def safe_cache_get(key: str, default: Any = None) -> Any:
    try:
        return cache.get(key, default)
    except Exception as exc:  # pragma: no cover - defensive fallback if Redis is down
        logger.warning("Redis cache get failed for %s: %s", key, exc)
        return default


def safe_cache_set(key: str, value: Any, timeout: int | None = None) -> None:
    try:
        cache.set(key, value, timeout)
    except Exception as exc:  # pragma: no cover - defensive fallback if Redis is down
        logger.warning("Redis cache set failed for %s: %s", key, exc)


def safe_cache_delete(key: str) -> None:
    try:
        cache.delete(key)
    except Exception as exc:  # pragma: no cover - defensive fallback if Redis is down
        logger.warning("Redis cache delete failed for %s: %s", key, exc)


def safe_cache_add(key: str, value: Any, timeout: int | None = None) -> bool:
    """Atomically add a key; returns True when this caller won the lock."""
    try:
        return bool(cache.add(key, value, timeout))
    except Exception as exc:  # pragma: no cover - defensive fallback if Redis is down
        logger.warning("Redis cache add failed for %s: %s", key, exc)
        return False


def safe_cache_incr_epoch(key: str = "epoch") -> int | None:
    try:
        try:
            return cache.incr(key)
        except ValueError:
            cache.set(key, 1)
            return 1
    except Exception as exc:  # pragma: no cover - defensive fallback if Redis is down
        logger.warning("Redis cache incr failed for %s: %s", key, exc)
        return None


def get_or_build(key: str, builder: Callable[[], Any], timeout: int | None = None) -> Any:
    """Return the cached value, building it at most once across concurrent callers.

    The winner of ``cache.add`` builds; the others poll briefly for its result
    instead of hammering the database (stampede protection).
    """
    cached = safe_cache_get(key)
    if cached is not None:
        return cached

    lock_key = f"lock:{key}"
    if safe_cache_add(lock_key, 1, LOCK_TIMEOUT):
        try:
            value = builder()
            safe_cache_set(key, value, timeout)
            return value
        finally:
            safe_cache_delete(lock_key)

    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(LOCK_POLL_SECONDS)
        cached = safe_cache_get(key)
        if cached is not None:
            return cached
    return builder()
