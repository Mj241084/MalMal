"""View decorators shared by the checkout and account flows."""

from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django_htmx.http import HttpResponseClientRedirect


def login_required_htmx(view):
    """Like login_required, but HTMX requests get HX-Redirect instead of a swapped login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        response = redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return HttpResponseClientRedirect(response.url) if request.htmx else response

    return wrapper
