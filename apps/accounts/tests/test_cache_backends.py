"""The cache backend is switchable (redis | database | locmem) without touching call sites."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.accounts import ratelimit
from config.settings.base import build_caches

REDIS = "django.core.cache.backends.redis.RedisCache"
DB = "django.core.cache.backends.db.DatabaseCache"
LOCMEM = "django.core.cache.backends.locmem.LocMemCache"


def test_redis_backend_keeps_the_previous_structure():
    caches = build_caches("redis", "redis://127.0.0.1:6379/1")

    assert caches["default"]["BACKEND"] == REDIS
    assert caches["ratelimit"]["BACKEND"] == REDIS
    assert caches["default"]["KEY_PREFIX"] == "mm:v1"
    assert caches["ratelimit"]["KEY_PREFIX"] == "mm:rl"
    assert caches["default"]["LOCATION"] == "redis://127.0.0.1:6379/1"
    # rate limits live in the next database index of the same server
    assert caches["ratelimit"]["LOCATION"] != caches["default"]["LOCATION"]
    assert caches["ratelimit"]["LOCATION"].endswith("/2")


def test_non_redis_backends_use_distinct_locations():
    for backend, engine in (("database", DB), ("locmem", LOCMEM)):
        caches = build_caches(backend)

        assert caches["default"]["BACKEND"] == engine
        assert caches["ratelimit"]["BACKEND"] == engine
        assert caches["default"]["LOCATION"] != caches["ratelimit"]["LOCATION"]
        assert caches["default"]["KEY_PREFIX"] == "mm:v1"
        assert caches["ratelimit"]["KEY_PREFIX"] == "mm:rl"


def test_unknown_backend_is_rejected():
    with pytest.raises(ImproperlyConfigured):
        build_caches("memcached")


def test_database_path_enforces_the_limit(settings):
    settings.CACHE_BACKEND = "database"

    assert [ratelimit.consume("t:limit", 2, 60) for _ in range(3)] == [True, True, False]


def test_database_path_refund_gives_one_hit_back(settings):
    settings.CACHE_BACKEND = "database"

    assert ratelimit.consume("t:refund", 1, 60) is True
    ratelimit.refund("t:refund")
    # without the refund this second hit would be over the limit of 1
    assert ratelimit.consume("t:refund", 1, 60) is True


def test_database_path_restarts_after_the_window(settings, monkeypatch):
    settings.CACHE_BACKEND = "database"
    now = [1_000.0]
    monkeypatch.setattr(ratelimit, "time", SimpleNamespace(time=lambda: now[0]))

    assert ratelimit.consume("t:window", 1, 60) is True
    assert ratelimit.consume("t:window", 1, 60) is False

    now[0] += 61
    assert ratelimit.consume("t:window", 1, 60) is True
