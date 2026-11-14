"""Account URLs: OTP login, profile, addresses."""

from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("auth/otp/modal/", views.otp_modal_view, name="otp_modal"),
    path("auth/otp/request/", views.otp_request_view, name="otp_request"),
    path("auth/otp/verify/", views.otp_verify_view, name="otp_verify"),
    path("auth/otp/cancel/", views.otp_cancel_view, name="otp_cancel"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/logout-all/", views.logout_all_view, name="logout_all"),
    path("account/", views.profile_view, name="profile"),
    path("account/addresses/", views.address_list, name="addresses"),
    path("account/addresses/new/", views.address_create, name="address_create"),
    path("account/addresses/<int:pk>/edit/", views.address_edit, name="address_edit"),
    path("account/addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("account/addresses/<int:pk>/default/", views.address_set_default, name="address_set_default"),
]
