"""Search URL patterns."""

from django.urls import path

from apps.search import views

app_name = "search"

urlpatterns = [
    path("search/", views.search_view, name="results"),
    path("search/suggest/", views.suggest_view, name="suggest"),
]
