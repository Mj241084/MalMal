from __future__ import annotations

from django.urls import path

from .views import account, auth, dashboard, shell

app_name = "panel"

urlpatterns = [
    path("account/", account.AccountView.as_view(), name="account"),
    path("search/", shell.search_view, name="search"),
    path("badges/", shell.badges_view, name="badges"),
    path("login/", auth.LoginView.as_view(), name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("", dashboard.DashboardView.as_view(), name="dashboard"),
]
