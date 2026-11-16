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
    context = {
        "can_orders": can_orders,
        "refunds": payment_services.refund_candidates().count() if user.has_perm("payments.view_payment") else 0,
    }
    if can_orders:
        context.update(to_ship=queries.orders_to_ship(), sales=queries.sales_last_30_days(), **queries.ship_queue(user))
    return render(request, "panel/dashboard.html", context)
