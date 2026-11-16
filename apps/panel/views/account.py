from __future__ import annotations

from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from apps.accounts.models import User
from apps.panel import audit, auth, htmx
from apps.panel.forms import PanelLoginForm, PasswordChangeForm
from apps.panel.permissions import panel_view


class AccountView(View):
    template_name = "panel/account.html"

    @panel_view(authenticated_only=True)
    def get(self, request):
        return render(request, self.template_name, {"form": PasswordChangeForm()})

    @panel_view(authenticated_only=True)
    def post(self, request):
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            if request.user.check_password(form.cleaned_data["old"]):
                request.user.set_password(form.cleaned_data["new1"])
                request.user.save()
                audit.log(request.user, request.user, audit.CHANGE, "تغییر رمز عبور")
                return htmx.toast(render(request, self.template_name, {"form": PasswordChangeForm()}), "رمز تغییر کرد")
            form.add_error("old", "رمز فعلی اشتباه است")
        return render(request, self.template_name, {"form": form}, status=400)
