"""Request helpers shared by views."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str | None:
    remote = (request.META.get("REMOTE_ADDR") or "").strip()
    if remote and remote in getattr(settings, "TRUSTED_PROXY_IPS", ()):
        x_real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
        if x_real:
            return x_real
        first = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        if first:
            return first
    return remote or None
