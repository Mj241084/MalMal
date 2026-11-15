"""Marketing URL patterns: collections."""

from django.urls import path

from apps.marketing import views

app_name = "marketing"

urlpatterns = [
    path("collections/", views.collection_list_view, name="collection_list"),
    path("collections/<str:slug>/", views.collection_view, name="collection"),
]
