"""Shared test fixtures: isolated Redis cache, clean FTS index, and geo data."""

from __future__ import annotations

import pytest
from django.core.cache import cache, caches
from django.db import connection
from django.test.testcases import DatabaseOperationForbidden

from apps.geo.models import City, Province


def _clear_fts() -> None:
    """The FTS table is not managed by Django, so rows survive table truncation."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM product_fts")
    except (DatabaseOperationForbidden, RuntimeError):
        # SimpleTestCase subclasses (and pytest-django's blocker) forbid DB access.
        return


@pytest.fixture(autouse=True)
def clean_cache_and_index():
    """Redis holds real counters and the FTS table is not managed by Django."""
    caches["ratelimit"].clear()
    cache.clear()
    _clear_fts()
    yield
    caches["ratelimit"].clear()
    cache.clear()


@pytest.fixture
def province(db) -> Province:
    return Province.objects.create(name="تهران", slug="tehran", sort=1)


@pytest.fixture
def city(db, province) -> City:
    return City.objects.create(province=province, name="تهران", slug="tehran")


@pytest.fixture
def other_province(db) -> Province:
    return Province.objects.create(name="اصفهان", slug="isfahan", sort=2)


@pytest.fixture
def other_city(db, other_province) -> City:
    return City.objects.create(province=other_province, name="اصفهان", slug="isfahan")
