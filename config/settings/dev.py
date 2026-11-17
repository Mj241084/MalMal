"""Development Django settings for MAL MAL."""

from config.env import get_env, get_env_bool, get_env_list
from config.settings.base import *  # noqa: F403
from config.settings.base import build_caches

DEBUG = get_env_bool("DEBUG", True)

SECRET_KEY = get_env(
    "DJANGO_SECRET_KEY",
    "django-insecure-malmal-local-dev-only-change-in-production",
)

ALLOWED_HOSTS = get_env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", "[::1]"])

REDIS_URL = get_env("REDIS_URL", "redis://127.0.0.1:6379/1")
CACHES = build_caches(REDIS_URL, get_env("RATELIMIT_REDIS_URL"))
