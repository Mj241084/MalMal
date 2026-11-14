"""Retention helpers. Today they run from the admin; Celery/cron will call the same functions (P6)."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.notifications.models import SmsLog

SMS_LOG_RETENTION = timedelta(days=90)


def purge_sms_logs(*, older_than: timedelta = SMS_LOG_RETENTION, queryset: QuerySet | None = None) -> int:
    """Delete SMS logs older than `older_than`."""
    cutoff = timezone.now() - older_than
    base = queryset if queryset is not None else SmsLog.objects.all()
    deleted, _ = base.filter(created_at__lt=cutoff).delete()
    return deleted
