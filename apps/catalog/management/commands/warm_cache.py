"""Warm the caches for the most-viewed products and the navigation menu (docs/03 §5).

Run after imports or on a cron/timer; the site works without it, this only removes
the first-hit latency for popular pages.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import F

from apps.catalog.cache import TTL_PRODUCT_DETAIL, get_or_build, product_detail_key
from apps.catalog.menu import navigation
from apps.catalog.models import Product
from apps.catalog.views import _render_detail

WARM_LIMIT = 200


class Command(BaseCommand):
    help = "Pre-build cached fragments for popular products and the menu."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=WARM_LIMIT)

    def handle(self, *args, **options):
        navigation()
        self.stdout.write("Menu cache warmed.")

        products = (
            Product.objects.filter(status=Product.STATUS_ACTIVE)
            .select_related("brand", "category", "main_image")
            .order_by(F("purchase_count_30d").desc(nulls_last=True), F("view_count").desc(nulls_last=True))[
                : options["limit"]
            ]
        )

        warmed = 0
        for product in products:
            get_or_build(product_detail_key(product), lambda p=product: _render_detail(p), TTL_PRODUCT_DETAIL)
            warmed += 1

        self.stdout.write(self.style.SUCCESS(f"Warmed {warmed} product detail fragment(s)."))
