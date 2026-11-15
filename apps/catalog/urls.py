"""Catalog URL patterns."""

from django.urls import path

from apps.catalog import views

app_name = "catalog"

urlpatterns = [
    path("c/<int:pk>/<str:slug>/", views.category_view, name="category"),
    path("p/<int:pk>/<str:slug>/", views.product_view, name="product"),
    path("p/<int:pk>/variant/<int:variant_id>/", views.variant_panel_view, name="variant_panel"),
    path("similar/<int:pk>/", views.similar_view, name="similar"),
    path("brands/<str:slug>/", views.brand_view, name="brand"),
]
