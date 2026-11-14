"""Rebuild the FTS5 product index (docs/03 §7)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.search.index import rebuild_all


class Command(BaseCommand):
    help = "Rebuild the product FTS5 index from scratch."

    def handle(self, *args, **options):
        count = rebuild_all()
        self.stdout.write(self.style.SUCCESS(f"Search index rebuilt with {count} product(s)."))
