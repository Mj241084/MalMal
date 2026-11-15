"""Printable order receipt, built only from the order snapshot (docs/02 §7)."""

from __future__ import annotations

from django.shortcuts import render

from apps.payments.models import Payment


def render_invoice(request, order):
    payment = order.payments.filter(status=Payment.VERIFIED).order_by("-verified_at").first()
    response = render(request, "pages/invoice.html", {"order": order, "payment": payment})
    response["Cache-Control"] = "private, no-store"
    return response
