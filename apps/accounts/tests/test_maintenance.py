"""Retention and admin purge tests for OTPChallenge (D33)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts import maintenance
from apps.accounts.models import OTPChallenge, User

pytestmark = pytest.mark.django_db


def _make_challenge(mobile: str, *, expires_delta: timedelta, locked_delta: timedelta | None = None) -> OTPChallenge:
    now = timezone.now()
    return OTPChallenge.objects.create(
        mobile=mobile,
        code_hmac="0" * 64,
        expires_at=now + expires_delta,
        locked_until=(now + locked_delta) if locked_delta is not None else None,
    )


def test_purge_otp_challenges_rules():
    now = timezone.now()
    stale = _make_challenge("09120000001", expires_delta=-timedelta(days=2))
    active = _make_challenge("09120000002", expires_delta=timedelta(minutes=2))
    locked_future = _make_challenge(
        "09120000003",
        expires_delta=-timedelta(days=5),
        locked_delta=timedelta(minutes=10),
    )
    other_stale = _make_challenge("09120000004", expires_delta=-timedelta(days=3))

    # Queryset filtering: only selected stale rows are purged
    deleted_subset = maintenance.purge_otp_challenges(
        queryset=OTPChallenge.objects.filter(pk=stale.pk),
    )
    assert deleted_subset == 1
    assert not OTPChallenge.objects.filter(pk=stale.pk).exists()
    assert OTPChallenge.objects.filter(pk=other_stale.pk).exists()

    # Full purge: active and future-locked challenges survive; remaining stale row is deleted
    assert active.expires_at > now
    deleted_rest = maintenance.purge_otp_challenges()
    assert deleted_rest == 1
    assert not OTPChallenge.objects.filter(pk=other_stale.pk).exists()
    assert OTPChallenge.objects.filter(pk=active.pk).exists()
    assert OTPChallenge.objects.filter(pk=locked_future.pk).exists()


def test_otp_challenge_admin_purge_action_permissions_and_execution(client):
    stale = _make_challenge("09120000011", expires_delta=-timedelta(days=2))
    url = reverse("admin:accounts_otpchallenge_changelist")

    staff = User.objects.create_user("09129000001", password="secret", is_staff=True)
    client.force_login(staff)
    resp_staff = client.post(url, {"action": "purge_stale", "_selected_action": [str(stale.pk)]})
    assert resp_staff.status_code in (302, 403)
    assert OTPChallenge.objects.filter(pk=stale.pk).exists()

    superuser = User.objects.create_superuser("09129000002", password="secret")
    client.force_login(superuser)
    changelist = client.get(url)
    assert "purge_stale" in changelist.content.decode()

    resp_super = client.post(
        url,
        {"action": "purge_stale", "_selected_action": [str(stale.pk)]},
        follow=True,
    )
    assert resp_super.status_code == 200
    assert not OTPChallenge.objects.filter(pk=stale.pk).exists()
    assert "۱ چالش پاک شد" in resp_super.content.decode() or "1 چالش پاک شد" in resp_super.content.decode()
