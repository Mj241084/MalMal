from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.panel import auth, htmx


class LoginView(View):
    template_name = "panel/login.html"

    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect("panel:dashboard")
        return render(request, self.template_name, {"next": request.GET.get("next")})

    def post(self, request):
        mobile = request.POST.get("mobile", "")
        password = request.POST.get("password", "")
        next_url = request.POST.get("next")
        
        status = auth.try_login(request, mobile, password)
        if status == auth.OK:
            return redirect(auth.safe_next(request, next_url))
        
        err = auth.LOGIN_FAILED if status == auth.INVALID else auth.LOGIN_THROTTLED
        if request.htmx:
            return htmx.toast(render(request, "panel/partials/login_form.html", {"error": err}), err, "error")
        messages.error(request, err)
        return render(request, self.template_name, {"error": err, "next": next_url})


def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect("panel:login")
