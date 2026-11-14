"""Core URL patterns."""

from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("r/<str:code>/", views.short_link_redirect_view, name="short_link"),
    path("pages/<str:slug>/", views.static_page_view, name="static_page"),
    path("_styleguide/", views.styleguide_view, name="styleguide"),
    path("_styleguide/ping/", views.styleguide_ping_view, name="styleguide_ping"),
]
