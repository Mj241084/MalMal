"""Engagement URL patterns."""

from django.urls import path

from apps.engagement import views

app_name = "engagement"

urlpatterns = [
    path("likes/state/", views.like_state_view, name="like_state"),
    path("likes/<int:pk>/", views.like_set_view, name="like_set"),
    path("social/product/<int:pk>/", views.product_social_view, name="product_social"),
    path("reviews/product/<int:pk>/", views.reviews_view, name="reviews"),
    path("account/wishlist/", views.wishlist_view, name="wishlist"),
]
