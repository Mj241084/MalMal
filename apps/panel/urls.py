from __future__ import annotations

from django.urls import path

from .views import (
    account,
    auth,
    brands,
    categories,
    dashboard,
    inventory,
    orders,
    payments,
    products,
    reviews,
    shell,
)

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
    # inventory
    path("inventory/", inventory.inventory_list, name="inventory"),
    path("inventory/ledger/", inventory.inventory_ledger, name="inventory_ledger"),
    path("inventory/variants/<int:variant_pk>/adjust/", inventory.stock_adjust, name="stock_adjust"),
    # reviews
    path("reviews/", reviews.review_list, name="reviews"),
    path("reviews/decide/", reviews.review_decide, name="review_decide"),
    path("reviews/<int:pk>/reply/", reviews.review_reply, name="review_reply"),
    # products
    path("products/", products.product_list, name="products"),
    path("products/bulk/", products.product_bulk, name="product_bulk"),
    path("products/new/", products.product_new, name="product_new"),
    path("products/<int:pk>/", products.product_studio, name="product_studio"),
    path("products/<int:pk>/quick/", products.product_quick, name="product_quick"),
    path("products/<int:pk>/basics/", products.product_basics, name="product_basics"),
    path("products/<int:pk>/publish/", products.product_publish, name="product_publish"),
    path("products/<int:pk>/delete/", products.product_delete, name="product_delete"),
    path("products/<int:pk>/images/", products.product_images, name="product_images"),
    path(
        "products/<int:pk>/images/<int:image_pk>/<str:action>/",
        products.product_image_action,
        name="product_image_action",
    ),
    path("products/<int:pk>/variants/new/", products.variant_new, name="variant_new"),
    path("products/<int:pk>/variants/<int:variant_pk>/", products.variant_edit, name="variant_edit"),
    path("products/<int:pk>/variants/<int:variant_pk>/<str:action>/", products.variant_action, name="variant_action"),
    path("products/<int:pk>/specs/", products.product_specs, name="product_specs"),
    path("products/<int:pk>/specs/<int:value_pk>/remove/", products.product_spec_remove, name="product_spec_remove"),
    # categories
    path("categories/", categories.category_list, name="categories"),
    path("categories/new/", categories.category_new, name="category_new"),
    path("categories/<int:pk>/", categories.category_edit, name="category_edit"),
    path("categories/<int:pk>/move/<str:direction>/", categories.category_move, name="category_move"),
    path("categories/<int:pk>/delete/", categories.category_delete, name="category_delete"),
    path("categories/<int:pk>/specs/new/", categories.spec_new, name="spec_new"),
    path("categories/<int:pk>/specs/<int:spec_pk>/", categories.spec_edit, name="spec_edit"),
    path("categories/<int:pk>/specs/<int:spec_pk>/<str:action>/", categories.spec_action, name="spec_action"),
    # brands
    path("brands/", brands.brand_list, name="brands"),
    path("brands/new/", brands.brand_new, name="brand_new"),
    path("brands/<int:pk>/edit/", brands.brand_edit, name="brand_edit"),
    path("brands/<int:pk>/delete/", brands.brand_delete, name="brand_delete"),
]
