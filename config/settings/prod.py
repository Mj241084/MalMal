"""Production Django settings for MAL MAL."""

from django.core.exceptions import ImproperlyConfigured

from config.env import get_env, get_env_bool, get_env_list
from config.settings.base import *  # noqa: F403
from config.settings.base import SITE_URL, SMSIR_API_KEY, build_caches

SMS_BACKEND = get_env("SMS_BACKEND", "smsir" if SMSIR_API_KEY else "console")

DEBUG = get_env_bool("DEBUG", False)

SECRET_KEY = get_env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required in production.")

REDIS_URL = get_env("REDIS_URL")
if not REDIS_URL:
    raise ImproperlyConfigured("REDIS_URL environment variable is required in production.")

ALLOWED_HOSTS = get_env_list("ALLOWED_HOSTS")

CACHES = build_caches(REDIS_URL, get_env("RATELIMIT_REDIS_URL"))

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Static files are collected and served by nginx; the manifest adds content hashes (D-P6 §9).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}

SECURE_SSL_REDIRECT = get_env_bool("SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = int(get_env("HSTS_SECONDS", str(60 * 60 * 24 * 30)))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = get_env_bool("HSTS_PRELOAD", False)
SILENCED_SYSTEM_CHECKS = ["security.W021"]  # preload is a one-way door: the owner decides
CSRF_TRUSTED_ORIGINS = get_env_list("CSRF_TRUSTED_ORIGINS", [SITE_URL])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"apps": {"level": "INFO"}},  # «refund needed» and SMS failures must reach journald
}
