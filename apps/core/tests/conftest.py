"""Pytest fixtures for isolated test cache cleanup."""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_test_cache():
    cache.clear()
    yield
    cache.clear()
