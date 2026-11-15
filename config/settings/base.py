"""Base Django settings for MAL MAL."""

from __future__ import annotations

from pathlib import Path

from config.env import derive_ratelimit_redis_url, get_env, get_env_bool, get_env_list, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "apps.core.apps.MalmalStaticFilesConfig",
    "django_htmx",
    "apps.core",
    "apps.catalog",
    "apps.search",
    "apps.marketing",
    "apps.geo",
    "apps.accounts",
    "apps.notifications",
    "apps.cart",
    "apps.orders",
    "apps.payments",
]

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/login/"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# SQLite with WAL, busy_timeout, foreign_keys, and IMMEDIATE write transactions
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "transaction_mode": "IMMEDIATE",
            "init_command": (
                "PRAGMA journal_mode=WAL;PRAGMA synchronous=NORMAL;PRAGMA busy_timeout=5000;PRAGMA foreign_keys=ON;"
            ),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Internationalization & Timezone
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# Sessions: signed cookies, server-side revocation via session_version (D02)
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days

# Static & Media
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# URLs & Admin
SITE_URL = get_env("SITE_URL", "http://localhost:8000").rstrip("/")
ADMIN_URL = get_env("ADMIN_URL", "admin/").lstrip("/")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"

# External integrations (non-blocking by default per D26)
SMSIR_API_KEY = get_env("SMSIR_API_KEY")
SMS_BACKEND = get_env("SMS_BACKEND", "console")
SMSIR_TEMPLATE_ID_OTP = get_env("SMSIR_TEMPLATE_ID_OTP")
SMSIR_TEMPLATE_ID_ORDER_PAID = get_env("SMSIR_TEMPLATE_ID_ORDER_PAID")
SMSIR_TEMPLATE_ID_ORDER_SHIPPED = get_env("SMSIR_TEMPLATE_ID_ORDER_SHIPPED")
SMSIR_TEMPLATE_ID_ORDER_SHIPPED_COURIER = get_env("SMSIR_TEMPLATE_ID_ORDER_SHIPPED_COURIER")
SMSIR_TEMPLATE_ID_ORDER_DELIVERED = get_env("SMSIR_TEMPLATE_ID_ORDER_DELIVERED")
SMSIR_TEMPLATE_ID_ORDER_CANCELLED = get_env("SMSIR_TEMPLATE_ID_ORDER_CANCELLED")
SMSIR_TEMPLATE_ID_ORDER_REFUNDED = get_env("SMSIR_TEMPLATE_ID_ORDER_REFUNDED")
SMSIR_TEMPLATE_ID_BACK_IN_STOCK = get_env("SMSIR_TEMPLATE_ID_BACK_IN_STOCK")
SMSIR_TEMPLATE_ID_ADMIN_NEW_ORDER = get_env("SMSIR_TEMPLATE_ID_ADMIN_NEW_ORDER")
SMS_ADMIN_MOBILES = get_env("SMS_ADMIN_MOBILES")

NESHAN_MAP_KEY = get_env("NESHAN_MAP_KEY")
NESHAN_SERVICE_KEY = get_env("NESHAN_SERVICE_KEY")

TRUSTED_PROXY_IPS = get_env_list("TRUSTED_PROXY_IPS")

ZARINPAL_MERCHANT_ID = get_env("ZARINPAL_MERCHANT_ID")
ZARINPAL_SANDBOX = get_env_bool("ZARINPAL_SANDBOX", True)

# Password validation (for staff admin accounts)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


def build_caches(redis_url: str) -> dict[str, dict]:
    """Configure RedisCache for general caching (mm:v1:) and a separate DB for rate limits."""
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_url,
            "KEY_PREFIX": "mm:v1",
            "KEY_FUNCTION": "apps.core.cache.make_key",
            "TIMEOUT": 60 * 60 * 24,  # 24h safety TTL
        },
        "ratelimit": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": derive_ratelimit_redis_url(redis_url),
            "KEY_PREFIX": "mm:rl",
            "KEY_FUNCTION": "apps.core.cache.make_key",
            "TIMEOUT": 60 * 60 * 24,
        },
    }
