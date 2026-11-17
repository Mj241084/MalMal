from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render
from django_htmx.http import trigger_client_event

LEVELS = {"success": messages.SUCCESS, "error": messages.ERROR, "warning": messages.WARNING, "info": messages.INFO}


def toast(response, message: str, level: str = "success"):
    return trigger_client_event(response, "mm:toast", {"message": message, "level": level})


def close_popover(response, popover_id: str):
    """Close a popover modal after a successful HTMX save (handled by panel.js)."""
    return trigger_client_event(response, "mm:popover-close", {"id": popover_id})


def flash(request, message: str, level: str = "success") -> None:
    """The same message for a request without HTMX (shown by the base template)."""
    messages.add_message(request, LEVELS.get(level, messages.INFO), message)


def page_or_partial(request, page: str, partial: str, context: dict, **kwargs):
    return render(request, partial if request.htmx else page, context, **kwargs)
