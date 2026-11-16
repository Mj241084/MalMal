from __future__ import annotations

from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.panel import auth
from apps.panel.permissions import public_view


@public_view
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        # Only a *panel* session skips the form: an admin-only session has no panel_login_at and would loop.
        if request.user.is_authenticated and request.user.is_staff and auth.session_state(request) == auth.STATE_OK:
            return redirect(auth.safe_next(request, request.GET.get("next")))
        return render(request, "panel/login.html", {"next": request.GET.get("next", "")})

    mobile = request.POST.get("mobile", "")
    next_url = request.POST.get("next", "")
    outcome = auth.try_login(request, mobile, request.POST.get("password", ""))
    if outcome == auth.OK:
        return redirect(auth.safe_next(request, next_url))
    error = auth.LOGIN_FAILED if outcome == auth.INVALID else auth.LOGIN_THROTTLED
    return render(request, "panel/login.html", {"next": next_url, "mobile": mobile, "error": error})


@public_view
@require_POST
def logout_view(request):
    logout(request)
    return redirect("panel:login")
