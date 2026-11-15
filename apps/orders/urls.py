from django.urls import path

from apps.orders import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/place/", views.place_view, name="place"),
    path("checkout/address/new/", views.address_new_view, name="address_new"),
    path("account/orders/", views.order_list_view, name="list"),
    path("account/orders/<str:number>/", views.order_detail_view, name="detail"),
    path("account/orders/<str:number>/pay/", views.pay_view, name="pay"),
    path("orders/<str:number>/result/", views.order_result_view, name="result"),
]
