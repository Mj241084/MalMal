from django.urls import path

from apps.cart import views

app_name = "cart"

urlpatterns = [
    path("cart/", views.detail_view, name="detail"),
    path("cart/render/", views.render_view, name="render"),
    path("cart/state/", views.state_view, name="state"),
    path("cart/add/", views.add_view, name="add"),
    path("cart/line/", views.line_view, name="line"),
    path("cart/set/", views.set_view, name="set"),
    path("cart/sync/", views.sync_view, name="sync"),
]
