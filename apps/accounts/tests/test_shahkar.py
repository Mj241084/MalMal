"""Shahkar rule: a national code is saved only when it matches the mobile (or checking is not configured)."""

from __future__ import annotations

import pytest

from apps.accounts import shahkar
from apps.accounts.forms import ProfileForm
from apps.accounts.models import User

CODE = "0012345679"


@pytest.fixture
def user(db):
    return User.objects.create_user("09121230009")


@pytest.fixture
def on(settings):
    settings.SHAHKAR_API_TOKEN = "token"


def _form(user):
    return ProfileForm({"first_name": "مریم", "last_name": "احمدی", "national_code": CODE, "email": ""}, instance=user)


def test_not_configured_skips_the_check(user, monkeypatch):
    monkeypatch.setattr(shahkar, "_call", lambda *args: pytest.fail("must not be called"))
    assert _form(user).is_valid()


def test_mismatch_blocks_and_keeps_the_other_fields(user, on, monkeypatch):
    monkeypatch.setattr(shahkar, "_call", lambda *args: False)
    form = _form(user)
    assert not form.is_valid()
    assert shahkar.MESSAGES[shahkar.MISMATCH] in form.errors["national_code"]
    assert form["first_name"].value() == "مریم"


def test_service_down_blocks_without_burning_attempts(user, on, monkeypatch):
    monkeypatch.setattr(shahkar, "_call", lambda *args: None)
    for _ in range(shahkar.ATTEMPTS_PER_HOUR + 1):
        form = _form(user)
        assert not form.is_valid()
    assert shahkar.MESSAGES[shahkar.UNAVAILABLE] in form.errors["national_code"]


def test_match_is_accepted_and_cached(user, on, monkeypatch):
    calls = []
    monkeypatch.setattr(shahkar, "_call", lambda *args: calls.append(args) or True)
    assert _form(user).is_valid()
    assert _form(user).is_valid()
    assert len(calls) == 1
