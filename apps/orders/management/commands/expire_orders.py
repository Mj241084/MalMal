"""Expire unpaid orders past their reservation and return the stock. Safe to run repeatedly."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.orders import services
from apps.orders.models import Order
from apps.payments import services as payment_services


class Command(BaseCommand):
    help = "Expire unpaid orders whose reservation ended (every 5 minutes; cron/timer lands in P6)."

    def handle(self, *args, **options):
        payment_services.requeue_stale_verifying()  # a crashed callback must not pin a reservation forever
        due = list(
            Order.objects.filter(status=Order.PENDING, reserved_until__lt=timezone.now()).values_list("pk", flat=True)
        )
        expired = sum(1 for pk in due if services.expire_order(pk))
        self.stdout.write(self.style.SUCCESS(f"{expired} order(s) expired."))
