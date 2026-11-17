"""Staff sign-in rules (docs/09 §2.4)."""

from __future__ import annotations

import time

from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts import ratelimit
from apps.core.text import normalize_digits
from apps.core.validators import normalize_iran_mobile

PANEL_PREFIX = "/panel/"
SESSION_KEY = "panel_login_at"
SESSION_MAX_AGE = 12 * 60 * 60

MOBILE_LIMIT, MOBILE_WINDOW = 5, 15 * 60

OK, INVALID, THROTTLED = "ok", "invalid", "throttled"
STATE_OK, STATE_MISSING, STATE_EXPIRED = "ok", "missing", "expired"

LOGIN_FAILED = "موبایل یا رمز درست نیست"
LOGIN_THROTTLED = "تلاش‌های ناموفق زیاد شد. چند دقیقه بعد دوباره امتحان کنید"


def _now() -> float:
    return time.time()


def session_state(request) -> str:
    started = request.session.get(SESSION_KEY)
    if not isinstance(started, int | float):
        return STATE_MISSING
    return STATE_OK if _now() - started <= SESSION_MAX_AGE else STATE_EXPIRED


def safe_next(request, value: str | None) -> str:
    value = (value or "").strip()
    if value.startswith(PANEL_PREFIX) and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return value
    return reverse("panel:dashboard")


def try_login(request, raw_mobile: str, password: str) -> str:
    try:
        mobile = normalize_iran_mobile(raw_mobile)
    except ValidationError:
        mobile = ""
    mobile_key = f"panel:login:m:{mobile or normalize_digits(raw_mobile).strip()[:20]}"

    if not ratelimit.consume(mobile_key, MOBILE_LIMIT, MOBILE_WINDOW):
        return THROTTLED

    user = authenticate(request, username=mobile, password=password) if mobile else None
    if user is None or not (user.is_active and user.is_staff):
        return INVALID

    login(request, user)
    request.session[SESSION_KEY] = int(_now())
    ratelimit.refund(mobile_key)
    return OK
