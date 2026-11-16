"""Search providers and navigation badges. Every panel phase appends its own here."""

from __future__ import annotations

from django.urls import reverse

from apps.orders.models import Order
from apps.panel import badges, queries, search
from apps.payments import services as payment_services


@badges.register("orders_to_ship")
def orders_to_ship() -> int:
    return queries.orders_to_ship()


@badges.register("refunds")
def refunds() -> int:
    return payment_services.refund_candidates().count()


@search.register("orders", "سفارش‌ها", "orders.view_order")
def find_orders(query: str) -> list[search.Hit]:
    condition = queries.order_search_q(query)
    if condition is None:
        return []
    rows = Order.objects.filter(condition).order_by("-created_at")[: search.PER_PROVIDER]
    return [
        search.Hit(
            o.number, f"{o.buyer_name} — {o.get_status_display()}", reverse("panel:order_detail", args=[o.number])
        )
        for o in rows
    ]
