from django.db.models import Q
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Product, Variant
from apps.core.text import normalize_fa
from apps.orders.models import Order
from apps.panel import badges, queries, search
from apps.payments import services as payment_services


@badges.register("reviews_pending")
def reviews_pending() -> int:
    return queries.reviews_pending()


@badges.register("orders_to_ship")
def orders_to_ship() -> int:
    return queries.orders_to_ship()


@badges.register("refunds")
def refunds() -> int:
    return payment_services.refund_candidates().count()


@search.register("orders", "سفارش‌ها", "orders.view_order")
def orders_search(query: str) -> list[search.Hit]:
    condition = queries.order_search_q(query)
    if condition is None:
        return []
    rows = Order.objects.filter(condition).order_by("-created_at", "-pk")[: search.PER_PROVIDER]
    return [
        search.Hit(
            title=order.number,
            subtitle=f"{order.buyer_name} — {order.get_status_display()}",
            url=reverse("panel:order_detail", args=[order.number]),
        )
        for order in rows
    ]


# change_product, not view_product: the studio the hit opens needs both, and a link that ends in a 403 is worse than no hit
@search.register("products", "محصولات", "catalog.change_product")
def products_search(query: str) -> list[search.Hit]:
    text = normalize_fa(query, for_search=True)[:60]
    if len(text) < search.MIN_LENGTH:
        return []
    by_sku = Variant.objects.filter(sku__icontains=text).values("product_id")
    rows = Product.objects.filter(Q(search_text__contains=text) | Q(pk__in=by_sku)).order_by("-created_at")
    return [
        search.Hit(
            title=product.title,
            subtitle=product.get_status_display(),
            url=reverse("panel:product_studio", args=[product.pk]),
        )
        for product in rows[: search.PER_PROVIDER]
    ]


@search.register("customers", "مشتریان", "accounts.view_user")
def customers_search(query: str) -> list[search.Hit]:
    condition = queries.customer_search_q(query)
    if condition is None:
        return []
    rows = User.objects.filter(is_staff=False).filter(condition).order_by("-date_joined")[: search.PER_PROVIDER]
    return [
        search.Hit(
            title=user.get_full_name() or user.mobile,
            subtitle=user.mobile,
            url=reverse("panel:customer_detail", args=[user.pk]),
        )
        for user in rows
    ]
