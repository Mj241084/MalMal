"""Production Django settings for MAL MAL."""

from django.core.exceptions import ImproperlyConfigured

from config.env import get_env, get_env_bool, get_env_list
from config.settings.base import *  # noqa: F403
from config.settings.base import SMSIR_API_KEY, build_caches

SMS_BACKEND = get_env("SMS_BACKEND", "smsir" if SMSIR_API_KEY else "console")

DEBUG = get_env_bool("DEBUG", False)

SECRET_KEY = get_env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required in production.")

REDIS_URL = get_env("REDIS_URL")
if not REDIS_URL:
    raise ImproperlyConfigured("REDIS_URL environment variable is required in production.")

ALLOWED_HOSTS = get_env_list("ALLOWED_HOSTS")

CACHES = build_caches(REDIS_URL)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
