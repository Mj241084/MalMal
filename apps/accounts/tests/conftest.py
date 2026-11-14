"""Fixtures shared by the accounts tests."""

from __future__ import annotations

import pytest

from apps.accounts import otp
from apps.accounts.models import User

MOBILE = "09121234567"
OTHER_MOBILE = "09127654321"
OTP_CODE = "1234"


@pytest.fixture(autouse=True)
def sms_console_settings(settings):
    """Tests never touch the network: the console backend always delivers."""
    settings.SMS_BACKEND = "console"
    settings.SMSIR_API_KEY = ""
    settings.SMSIR_TEMPLATE_ID_OTP = ""


@pytest.fixture
def fixed_otp_code(monkeypatch) -> str:
    monkeypatch.setattr(otp, "generate_code", lambda: OTP_CODE)
    return OTP_CODE


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(MOBILE, first_name="مریم", last_name="احمدی")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(OTHER_MOBILE)
