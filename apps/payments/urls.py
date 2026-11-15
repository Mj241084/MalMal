from django.urls import path

from apps.payments import views

app_name = "payments"

urlpatterns = [
    path("callback/<slug:code>/", views.callback_view, name="callback"),
    path("fake/<str:authority>/", views.fake_bank_view, name="fake_bank"),
]
