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
