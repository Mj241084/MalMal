"""Small HTMX response helpers shared by panel views."""

from __future__ import annotations

from django.shortcuts import render
from django_htmx.http import trigger_client_event


def toast(response, message: str, level: str = "success"):
    return trigger_client_event(response, "mm:toast", {"message": message, "level": level})


def page_or_partial(request, page: str, partial: str, context: dict, **kwargs):
    return render(request, partial if request.htmx else page, context, **kwargs)
