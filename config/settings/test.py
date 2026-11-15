"""Test settings with isolated Redis cache prefix so tests never pollute dev cache."""

from config.settings.dev import *  # noqa: F403
from config.settings.dev import CACHES

CACHES = {
    "default": {
        **CACHES["default"],
        "KEY_PREFIX": "mm:test",
    },
    "ratelimit": {
        **CACHES["ratelimit"],
        "KEY_PREFIX": "mm:test:rl",
    },
}

# File-based test DB: concurrency tests need real SQLite locking (in-memory shared cache behaves differently).
DATABASES = {"default": {**DATABASES["default"], "TEST": {"NAME": BASE_DIR / "test_db.sqlite3"}}}  # noqa: F405
