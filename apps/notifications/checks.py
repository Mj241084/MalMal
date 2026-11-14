"""Deployment checks for SMS delivery configuration."""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def sms_backend_is_real(app_configs, **kwargs):
    if settings.SMS_BACKEND == "console":
        return [Error("SMS_BACKEND=console: OTP codes go to the log, not to customers.", id="notifications.E001")]
    return []
