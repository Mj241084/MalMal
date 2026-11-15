"""Repair drift in like/review counters from the source rows. Nightly (cron/timer lands in P6)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.engagement import counters


class Command(BaseCommand):
    help = "Recompute like_count, review_count, rating_sum and rating_avg for every product."

    def handle(self, *args, **options):
        fixed = counters.reconcile()
        self.stdout.write(self.style.SUCCESS(f"{fixed} product(s) corrected."))
