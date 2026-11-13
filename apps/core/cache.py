"""Redis cache key helpers and safe accessors."""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)


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
