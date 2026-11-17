"""OTP service behavior: storage, reuse, expiry, attempts, locks, and limits (docs/02 §4)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.cache import caches
from django.utils import timezone

from apps.accounts import otp, ratelimit
from apps.accounts.models import OTPChallenge, User
from apps.notifications import sms
from apps.notifications.models import SmsLog

MOBILE = "09121234567"

pytestmark = pytest.mark.django_db


def _expire(mobile: str = MOBILE) -> None:
    OTPChallenge.objects.filter(mobile=mobile).update(expires_at=timezone.now() - timedelta(seconds=1))


def test_code_is_stored_only_as_keyed_hmac(fixed_otp_code):
    result = otp.request_code(MOBILE)

    assert result.ok
    challenge = OTPChallenge.objects.get(mobile=MOBILE)
    assert challenge.code_hmac == otp.code_hmac(MOBILE, fixed_otp_code)
    assert fixed_otp_code not in challenge.code_hmac
    log = SmsLog.objects.get()
    assert log.mobile == MOBILE
    # The mobile itself contains "1234", so only the other fields are checked for the code.
    assert fixed_otp_code not in f"{log.kind} {log.provider_message_id} {log.error}"


def test_second_request_reuses_the_active_code_without_another_sms(fixed_otp_code):
    assert otp.request_code(MOBILE).status == otp.STATUS_SENT

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_REUSED
    assert 0 < result.seconds_remaining <= 120
    assert SmsLog.objects.count() == 1


def test_expired_challenge_is_replaced_and_counted(fixed_otp_code):
    otp.request_code(MOBILE)
    _expire()

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_SENT
    assert OTPChallenge.objects.count() == 1
    assert SmsLog.objects.count() == 2


def test_four_wrong_attempts_then_lock(fixed_otp_code):
    otp.request_code(MOBILE)

    remaining = []
    for _ in range(4):
        result = otp.verify_code(MOBILE, "9999")
        assert result.status == otp.VERIFY_INVALID
        remaining.append(result.attempts_remaining)

    assert remaining == [4, 3, 2, 1]

    locked = otp.verify_code(MOBILE, "9999")
    assert locked.status == otp.VERIFY_LOCKED
    assert 890 < locked.lock_seconds <= 900

    assert otp.verify_code(MOBILE, fixed_otp_code).status == otp.VERIFY_LOCKED
    assert otp.request_code(MOBILE).status == otp.STATUS_LOCKED


def test_correct_code_is_consumed_once(fixed_otp_code):
    otp.request_code(MOBILE)

    assert otp.verify_code(MOBILE, fixed_otp_code).status == otp.VERIFY_OK
    assert otp.verify_code(MOBILE, fixed_otp_code).status == otp.VERIFY_INVALID
    assert otp.request_code(MOBILE).status == otp.STATUS_SENT
    assert SmsLog.objects.count() == 2


def test_verify_code_with_persian_digits_succeeds(fixed_otp_code):
    otp.request_code(MOBILE)
    assert otp.verify_code(MOBILE, "۱۲۳۴").status == otp.VERIFY_OK


def test_challenge_with_max_attempts_is_inactive_after_lock_expiry(fixed_otp_code):
    otp.request_code(MOBILE)
    for _ in range(5):
        otp.verify_code(MOBILE, "9999")

    challenge = OTPChallenge.objects.get(mobile=MOBILE)
    assert challenge.attempts >= challenge.max_attempts
    # Past the lock window
    challenge.locked_until = timezone.now() - timedelta(minutes=1)
    challenge.save()
    assert challenge.is_active is False


def test_expired_code_is_rejected(fixed_otp_code):
    otp.request_code(MOBILE)
    _expire()

    assert otp.verify_code(MOBILE, fixed_otp_code).status == otp.VERIFY_EXPIRED


def test_missing_and_malformed_codes():
    assert otp.verify_code(MOBILE, "1234").status == otp.VERIFY_MISSING
    assert otp.verify_code(MOBILE, "12").status == otp.VERIFY_INVALID
    assert otp.verify_code(MOBILE, "abcd").status == otp.VERIFY_INVALID


def test_hourly_limit_per_mobile(fixed_otp_code, monkeypatch):
    monkeypatch.setattr(ratelimit, "MOBILE_HOURLY_LIMIT", 2)

    assert otp.request_code(MOBILE).ok
    _expire()
    assert otp.request_code(MOBILE).ok
    _expire()

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_RATE_LIMITED
    assert result.retry_after == ratelimit.HOUR


def test_daily_limit_per_mobile_and_hourly_counter_is_refunded(fixed_otp_code, monkeypatch):
    monkeypatch.setattr(ratelimit, "MOBILE_HOURLY_LIMIT", 10)
    monkeypatch.setattr(ratelimit, "MOBILE_DAILY_LIMIT", 2)

    assert otp.request_code(MOBILE).ok
    _expire()
    assert otp.request_code(MOBILE).ok
    _expire()

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_RATE_LIMITED
    assert result.retry_after == ratelimit.DAY
    assert caches["ratelimit"].get(f"otp:mobile:{MOBILE}:h") == 2


def test_send_failure_leaves_no_challenge_and_refunds_the_counters(fixed_otp_code, monkeypatch):
    monkeypatch.setattr(ratelimit, "MOBILE_HOURLY_LIMIT", 1)
    real_send = sms.send_template
    state = {"fail": True}

    def maybe_fail(key, mobile, params=None):
        if state["fail"]:
            return SmsLog(mobile=mobile, kind=key, status=SmsLog.STATUS_FAILED)
        return real_send(key, mobile, params)

    monkeypatch.setattr(sms, "send_template", maybe_fail)

    failed = otp.request_code(MOBILE)
    assert failed.status == otp.STATUS_SEND_FAILED
    assert not OTPChallenge.objects.exists()

    state["fail"] = False
    assert otp.request_code(MOBILE).status == otp.STATUS_SENT


def test_unconfigured_template_makes_otp_unavailable(settings, fixed_otp_code):
    settings.SMS_BACKEND = "smsir"
    settings.SMSIR_TEMPLATE_ID_OTP = ""

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_UNAVAILABLE
    assert not OTPChallenge.objects.exists()
    assert not SmsLog.objects.exists()


def test_missing_api_key_is_a_send_failure(settings, fixed_otp_code):
    settings.SMS_BACKEND = "smsir"
    settings.SMSIR_TEMPLATE_ID_OTP = "123456"
    settings.SMSIR_API_KEY = ""

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_SEND_FAILED
    assert not OTPChallenge.objects.exists()
    assert SmsLog.objects.get().status == SmsLog.STATUS_FAILED


def test_staff_mobiles_never_receive_sms(fixed_otp_code):
    User.objects.create_user(MOBILE, password="secret", is_staff=True)

    result = otp.request_code(MOBILE)

    assert result.status == otp.STATUS_SENT
    assert not SmsLog.objects.exists()
    assert otp.verify_code(MOBILE, fixed_otp_code).status == otp.VERIFY_OK


def test_mobile_is_normalized_before_storage(fixed_otp_code):
    result = otp.request_code("+98 912 123 4567")

    assert result.ok
    assert OTPChallenge.objects.get().mobile == MOBILE


def test_invalid_mobile_is_rejected(fixed_otp_code):
    assert otp.request_code("not-a-mobile").status == otp.STATUS_SEND_FAILED
    assert not SmsLog.objects.exists()


def test_dev_echo_code_respects_debug_and_backend(settings, capsys):
    settings.SMS_BACKEND = "console"
    settings.DEBUG = False
    otp._dev_echo_code(MOBILE, "1234")
    captured = capsys.readouterr()
    assert captured.out == ""

    settings.DEBUG = True
    otp._dev_echo_code(MOBILE, "1234")
    captured = capsys.readouterr()
    assert "[DEV OTP]" in captured.out
    assert "1234" in captured.out
