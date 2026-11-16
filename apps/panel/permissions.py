"""One decorator for every panel view: staff login, 12h session, explicit permission rule (D37)."""

from __future__ import annotations

from collections.abc import Sequence
from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect, render
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect

from apps.panel import auth


def _login_redirect(request):
    is_htmx = bool(getattr(request, "htmx", False))
    target = ""
    if is_htmx:
        target = request.htmx.current_url_abs_path or ""
    elif request.method == "GET":
        target = request.get_full_path()
    url = reverse("panel:login")
    if target.startswith(auth.PANEL_PREFIX):
        url = f"{url}?{urlencode({'next': target})}"
    return HttpResponseClientRedirect(url) if is_htmx else redirect(url)


def _forbidden(request):
    return render(request, "panel/403.html", status=403)


def public_view(view):
    view.panel_rule = None
    return view


def panel_view(
    *perms: str,
    any_of: Sequence[str] = (),
    superuser: bool = False,
    authenticated_only: bool = False,
):
    if not (perms or any_of or superuser or authenticated_only):
        raise ImproperlyConfigured("panel_view needs an explicit rule: perms, any_of, superuser or authenticated_only.")

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not (user.is_authenticated and user.is_active and user.is_staff):
                return _login_redirect(request)
            state = auth.session_state(request)
            if state != auth.STATE_OK:
                if state == auth.STATE_EXPIRED:
                    logout(request)
                return _login_redirect(request)
            if superuser and not user.is_superuser:
                return _forbidden(request)
            if perms and not user.has_perms(perms):
                return _forbidden(request)
            if any_of and not any(user.has_perm(p) for p in any_of):
                return _forbidden(request)
            return view(request, *args, **kwargs)

        wrapper.panel_rule = {
            "perms": tuple(perms),
            "any_of": tuple(any_of),
            "superuser": superuser,
            "authenticated_only": authenticated_only,
        }
        return wrapper

    return decorator
