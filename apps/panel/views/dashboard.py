from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.panel import queries
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services


@panel_view(authenticated_only=True)
@require_GET
def dashboard(request):
    user = request.user
    can_orders = user.has_perm("orders.view_order")
    can_reviews = user.has_perm("engagement.view_review")
    can_stock = user.has_perm("catalog.view_variant")
    context = {
        "can_orders": can_orders,
        "can_reviews": can_reviews,
        "can_stock": can_stock,
        "refunds": payment_services.refund_candidates().count() if user.has_perm("payments.view_payment") else 0,
    }
    if can_orders:
        context.update(to_ship=queries.orders_to_ship(), sales=queries.sales_last_30_days(), **queries.ship_queue(user))
    if can_reviews:
        context.update(reviews_pending=queries.reviews_pending(), **queries.review_queue(user))
    if can_stock:
        context.update(stock_alerts=queries.stock_alert_count(), wanted=queries.wanted_out_of_stock())
    return render(request, "panel/dashboard.html", context)
