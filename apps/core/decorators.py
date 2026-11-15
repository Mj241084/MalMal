"""View decorators shared by the checkout, account and engagement flows."""

from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django_htmx.http import HttpResponseClientRedirect


def htmx_login_redirect(request):
    """Send a signed-out visitor to login. HTMX requests come back to the page they were on, not to the POST URL."""
    target = (request.htmx.current_url_abs_path if request.htmx else None) or request.get_full_path()
    response = redirect_to_login(target, settings.LOGIN_URL)
    return HttpResponseClientRedirect(response.url) if request.htmx else response


def login_required_htmx(view):
    """Like login_required, but HTMX requests get HX-Redirect instead of a swapped login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        return htmx_login_redirect(request)

    return wrapper
