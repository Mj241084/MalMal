"""Rebuild purchase_count_30d from the daily ledger. Nightly (cron/timer lands in P6)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.engagement import counters


class Command(BaseCommand):
    help = "Recompute the rolling 30-day purchase counter and trim old ledger rows."

    def handle(self, *args, **options):
        fixed = counters.recount_purchases()
        self.stdout.write(self.style.SUCCESS(f"{fixed} product(s) corrected."))
