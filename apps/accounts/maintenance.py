"""Retention helpers. Today they run from the admin; Celery/cron will call the same functions (P6)."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import OTPChallenge

OTP_RETENTION = timedelta(days=1)


def purge_otp_challenges(*, older_than: timedelta = OTP_RETENTION, queryset: QuerySet | None = None) -> int:
    """Delete challenges that expired (and are no longer locked) more than `older_than` ago.

    A row that is still locked is kept: deleting it would lift the lock early.
    """
    cutoff = timezone.now() - older_than
    base = queryset if queryset is not None else OTPChallenge.objects.all()
    stale = base.filter(expires_at__lt=cutoff).filter(Q(locked_until__isnull=True) | Q(locked_until__lt=cutoff))
    deleted, _ = stale.delete()
    return deleted
