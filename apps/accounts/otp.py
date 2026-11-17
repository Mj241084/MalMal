"""OTP login service (docs/02 §4).

The service owns all OTP rules; views only translate results to UI. The code is
stored exclusively as a keyed HMAC (never plaintext, never in `SmsLog`).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts import ratelimit
from apps.accounts.models import OTPChallenge, User
from apps.core.models import SiteSettings
from apps.core.text import normalize_digits
from apps.core.validators import normalize_iran_mobile
from apps.notifications import sms

logger = logging.getLogger(__name__)

CODE_LENGTH = 4

STATUS_SENT = "sent"
STATUS_REUSED = "reused"
STATUS_LOCKED = "locked"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_UNAVAILABLE = "unavailable"
STATUS_SEND_FAILED = "send_failed"

VERIFY_OK = "ok"
VERIFY_INVALID = "invalid"
VERIFY_EXPIRED = "expired"
VERIFY_LOCKED = "locked"
VERIFY_MISSING = "missing"


@dataclass(frozen=True)
class OTPRequestResult:
    status: str
    seconds_remaining: int = 0
    lock_seconds: int = 0
    retry_after: int = 0

    @property
    def ok(self) -> bool:
        return self.status in (STATUS_SENT, STATUS_REUSED)


@dataclass(frozen=True)
class OTPVerifyResult:
    status: str
    mobile: str = ""
    attempts_remaining: int = 0
    lock_seconds: int = 0

    @property
    def ok(self) -> bool:
        return self.status == VERIFY_OK


def generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def code_hmac(mobile: str, code: str) -> str:
    key = str(settings.SECRET_KEY).encode("utf-8")
    message = f"{mobile}:{code}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _normalize(mobile: str | None) -> str | None:
    try:
        return normalize_iran_mobile(mobile)
    except ValidationError:
        return None


def _is_staff_mobile(mobile: str) -> bool:
    return User.objects.filter(mobile=mobile, is_staff=True).exists()


def _settings_values() -> tuple[int, int, int]:
    site = SiteSettings.get_solo()
    ttl = max(30, int(site.otp_ttl_seconds or 120))
    max_attempts = max(1, int(site.otp_max_attempts or 5))
    lock_minutes = max(1, int(site.otp_lock_minutes or 15))
    return ttl, max_attempts, lock_minutes


def _dev_echo_code(mobile: str, code: str) -> None:
    """DEV ONLY (TODO-SMSIR): sms.ir templates are not approved yet, so echo the code while testing.

    Runs only with DEBUG=True and the console SMS backend; delete once the real OTP template is live.
    """
    if settings.DEBUG and sms.backend_name() == "console":
        logger.warning("DEV OTP for %s: %s", mobile, code)
        print(f"[DEV OTP] {mobile}: {code}")  # noqa: T201


def request_code(mobile: str, ip: str | None = None) -> OTPRequestResult:
    """Request (or reuse) an OTP challenge for `mobile`.

    Responses deliberately do not reveal whether a customer account exists.
    A send failure never leaves behind an active challenge or consumed counters.
    """
    normalized = _normalize(mobile)
    if normalized is None:
        return OTPRequestResult(STATUS_SEND_FAILED)

    ttl_seconds, max_attempts, _ = _settings_values()

    challenge = OTPChallenge.objects.filter(mobile=normalized).first()
    if challenge is not None and challenge.is_locked:
        return OTPRequestResult(STATUS_LOCKED, lock_seconds=challenge.lock_seconds_remaining)

    if challenge is not None and challenge.is_active:
        return OTPRequestResult(STATUS_REUSED, seconds_remaining=challenge.seconds_remaining)

    # A real backend with no OTP template cannot deliver the code at all.
    if not sms.template_is_configured("otp"):
        logger.warning("OTP requested but the sms.ir OTP template id is not configured.")
        return OTPRequestResult(STATUS_UNAVAILABLE)

    mobile_h, mobile_d = ratelimit.otp_keys(normalized)
    taken: list[str] = []

    def release() -> None:
        for key in taken:
            ratelimit.refund(key)

    for key, limit, window in (
        (mobile_h, ratelimit.MOBILE_HOURLY_LIMIT, ratelimit.HOUR),
        (mobile_d, ratelimit.MOBILE_DAILY_LIMIT, ratelimit.DAY),
        (ratelimit.GLOBAL_KEY, ratelimit.GLOBAL_HOURLY_LIMIT, ratelimit.HOUR),
    ):
        if not ratelimit.consume(key, limit, window):
            release()
            return OTPRequestResult(STATUS_RATE_LIMITED, retry_after=window)
        taken.append(key)

    code = generate_code()
    _dev_echo_code(normalized, code)
    digest = code_hmac(normalized, code)

    # Staff accounts authenticate with a password; never send them an OTP.
    if _is_staff_mobile(normalized):
        logger.info("OTP suppressed for staff mobile %s.", normalized)
        _store_challenge(normalized, digest, ttl_seconds, max_attempts, ip)
        return OTPRequestResult(STATUS_SENT, seconds_remaining=ttl_seconds)

    # No DB transaction is open here: the network call happens before the challenge is stored.
    log = sms.send_template("otp", normalized, {"CODE": code})
    if log.status != log.STATUS_SENT:
        release()
        return OTPRequestResult(STATUS_SEND_FAILED)

    _store_challenge(normalized, digest, ttl_seconds, max_attempts, ip)
    return OTPRequestResult(STATUS_SENT, seconds_remaining=ttl_seconds)


def _store_challenge(
    mobile: str,
    digest: str,
    ttl_seconds: int,
    max_attempts: int,
    ip: str | None,
) -> None:
    now = timezone.now()
    with transaction.atomic():
        OTPChallenge.objects.update_or_create(
            mobile=mobile,
            defaults={
                "code_hmac": digest,
                "expires_at": now + timedelta(seconds=ttl_seconds),
                "last_sent_at": now,
                "attempts": 0,
                "max_attempts": max_attempts,
                "locked_until": None,
                "consumed_at": None,
                "ip": ip,
            },
        )


def verify_code(mobile: str, code: str) -> OTPVerifyResult:
    """Check a submitted code atomically in constant time and consume the challenge once."""
    normalized = _normalize(mobile)
    submitted = normalize_digits(code).strip()
    if normalized is None or len(submitted) != CODE_LENGTH or not submitted.isascii() or not submitted.isdigit():
        return OTPVerifyResult(VERIFY_INVALID)

    _, _, lock_minutes = _settings_values()

    with transaction.atomic():
        challenge = OTPChallenge.objects.filter(mobile=normalized).first()
        if challenge is None:
            return OTPVerifyResult(VERIFY_MISSING)

        if challenge.is_locked:
            return OTPVerifyResult(VERIFY_LOCKED, lock_seconds=challenge.lock_seconds_remaining)
        if challenge.consumed_at is not None:
            return OTPVerifyResult(VERIFY_INVALID)
        if challenge.expires_at <= timezone.now():
            return OTPVerifyResult(VERIFY_EXPIRED)
        if challenge.attempts >= challenge.max_attempts:
            challenge.locked_until = timezone.now() + timedelta(minutes=lock_minutes)
            challenge.save(update_fields=["locked_until"])
            return OTPVerifyResult(VERIFY_LOCKED, lock_seconds=challenge.lock_seconds_remaining)

        now = timezone.now()
        challenge.attempts += 1
        matches = hmac.compare_digest(challenge.code_hmac, code_hmac(normalized, submitted))

        if matches:
            challenge.consumed_at = now
            challenge.save(update_fields=["attempts", "consumed_at"])
            return OTPVerifyResult(VERIFY_OK, mobile=normalized)

        if challenge.attempts >= challenge.max_attempts:
            challenge.locked_until = now + timedelta(minutes=lock_minutes)
            challenge.save(update_fields=["attempts", "locked_until"])
            return OTPVerifyResult(
                VERIFY_LOCKED,
                lock_seconds=challenge.lock_seconds_remaining,
            )

        challenge.save(update_fields=["attempts"])
        return OTPVerifyResult(
            VERIFY_INVALID,
            attempts_remaining=max(0, challenge.max_attempts - challenge.attempts),
        )
