from __future__ import annotations

from django.urls import path

from .views import account, auth, dashboard, orders, payments, shell

app_name = "panel"

urlpatterns = [
    path("", dashboard.dashboard, name="dashboard"),
    path("login/", auth.login_view, name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("account/", account.account, name="account"),
    path("account/logout-all/", account.logout_all, name="logout_all"),
    path("search/", shell.search_view, name="search"),
    path("badges/", shell.badges_view, name="badges"),
    path("orders/", orders.order_list, name="orders"),
    path("orders/bulk/", orders.order_bulk, name="order_bulk"),  # before <number>
    path("orders/<str:number>/", orders.order_detail, name="order_detail"),
    path("orders/<str:number>/status/", orders.order_status, name="order_status"),
    path("orders/<str:number>/sms/", orders.order_resend_sms, name="order_resend_sms"),
    path("orders/<str:number>/invoice/", orders.order_invoice, name="order_invoice"),
    path("payments/", payments.payment_list, name="payments"),
    path("payments/<int:pk>/refund/", payments.payment_refund, name="payment_refund"),
]
