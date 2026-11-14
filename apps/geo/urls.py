"""Geo URLs."""

from django.urls import path

from apps.geo import views

app_name = "geo"

urlpatterns = [
    path("cities/", views.city_options, name="city_options"),
    path("reverse/", views.reverse_geocode, name="reverse_geocode"),
]
