"""Shahkar Lite (api.ir): does this national code belong to the owner of this mobile number?

The network call never runs inside a transaction: callers validate forms first (CLAUDE.md §4).
No token configured = nothing is checked (D26). With a token, an answer we cannot get blocks the save,
because a national code is locked after the first save (D20) and the customer cannot fix a wrong one.
"""

from __future__ import annotations

import hashlib
import json
import logging
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.accounts import ratelimit
from apps.core.cache import safe_cache_get, safe_cache_set

logger = logging.getLogger(__name__)

URL = "https://s.api.ir/api/sw1/ShahkarLite"
TIMEOUT = 6  # seconds; a customer is waiting
ATTEMPTS_PER_HOUR = 5
OK_TTL = 60 * 30

MATCH, MISMATCH, UNAVAILABLE, THROTTLED, SKIPPED = "match", "mismatch", "unavailable", "throttled", "skipped"
MESSAGES = {
    MISMATCH: "این کد ملی با شماره‌ی موبایل شما مطابقت ندارد",
    UNAVAILABLE: "تطبیق کد ملی اکنون ممکن نیست؛ چند دقیقه بعد دوباره تلاش کنید",
    THROTTLED: "تعداد تلاش‌ها زیاد شد؛ یک ساعت بعد دوباره تلاش کنید",
}


def _call(mobile: str, national_code: str) -> bool | None:
    """True or False = the service answered; None = no usable answer.

    [VERIFY] The decision rests on `data` only. The sample answer in the provider docs shows `data: true`
    next to `success: false`, so `success` is logged, never used.
    """
    request = Request(
        URL,
        data=json.dumps({"nationalCode": national_code, "mobile": mobile}).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {settings.SHAHKAR_API_TOKEN}",
        },
    )
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:  # before OSError: HTTPError is one
        logger.error("Shahkar answered HTTP %s", exc.code)
        return None
    except (OSError, ValueError) as exc:  # URLError, timeouts, bad JSON
        logger.warning("Shahkar request failed: %s", exc.__class__.__name__)
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, bool):
        logger.error("Shahkar answer has no boolean `data`")
        return None
    logger.info("Shahkar data=%s success=%s code=%s", data, payload.get("success"), payload.get("code"))
    return data


def verify(user_id: int, mobile: str, national_code: str) -> str:
    if not settings.SHAHKAR_API_TOKEN:
        return SKIPPED
    pair = hashlib.sha256(f"{mobile}:{national_code}".encode()).hexdigest()[:32]  # no personal data in Redis keys
    ok_key = f"shahkar:ok:{pair}"
    if safe_cache_get(ok_key):
        return MATCH
    limit_key = f"shahkar:u:{user_id}"
    if not ratelimit.consume(limit_key, ATTEMPTS_PER_HOUR, ratelimit.HOUR):
        return THROTTLED
    answer = _call(mobile, national_code)
    if answer is None:
        ratelimit.refund(limit_key)  # our side or the provider's trouble must not burn the customer's attempts
        return UNAVAILABLE
    if answer:
        safe_cache_set(ok_key, 1, OK_TTL)
        return MATCH
    return MISMATCH


def check_form(form, *, user_id: int, mobile: str, national_code: str) -> None:
    """Add an error on `national_code` unless Shahkar confirms the pair (or checking is off)."""
    status = verify(user_id, mobile, national_code)
    if status not in (MATCH, SKIPPED):
        form.add_error("national_code", MESSAGES[status])
