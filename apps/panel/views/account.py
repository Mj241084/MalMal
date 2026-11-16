from __future__ import annotations

from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import F
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.panel import audit, htmx
from apps.panel.forms import PasswordChangeForm
from apps.panel.permissions import panel_view


@panel_view(authenticated_only=True)
@require_http_methods(["GET", "POST"])
def account(request):
    form = PasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, new = request.user, form.cleaned_data["new1"]
        if not user.check_password(form.cleaned_data["old"]):
            form.add_error("old", "رمز فعلی درست نیست")
        else:
            try:
                validate_password(new, user)
            except ValidationError as exc:
                form.add_error("new1", exc)
            else:
                user.set_password(new)
                user.session_version += 1  # every other session ends; this one is kept below
                user.save(update_fields=["password", "session_version"])
                update_session_auth_hash(request, user)
                audit.log(user, user, audit.CHANGE, "تغییر رمز عبور")
                htmx.flash(request, "رمز تغییر کرد")
                return redirect("panel:account")
    return render(request, "panel/account.html", {"form": form})


@panel_view(authenticated_only=True)
@require_POST
def logout_all(request):
    User.objects.filter(pk=request.user.pk).update(session_version=F("session_version") + 1)
    logout(request)
    return redirect("panel:login")
