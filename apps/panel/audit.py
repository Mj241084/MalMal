"""Panel audit trail on django.contrib.admin.LogEntry (D38)."""

from __future__ import annotations

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry

PREFIX = "[panel] "

__all__ = ["ADDITION", "CHANGE", "DELETION", "PREFIX", "log"]


def log(user, obj, action: int, message: str = "") -> LogEntry:
    return LogEntry.objects.log_actions(
        user_id=user.pk,
        queryset=[obj],
        action_flag=action,
        change_message=f"{PREFIX}{message}".strip(),
        single_object=True,
    )
