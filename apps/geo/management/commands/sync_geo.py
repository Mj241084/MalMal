"""Copy every province and city from Neshan into our database: the fallback copy used when Neshan is down."""

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.geo import services
from apps.geo.models import City, Province


class Command(BaseCommand):
    help = "Copy all provinces and cities from the Neshan Region API into the database (safe to re-run; never deletes)."

    def handle(self, *args, **options):
        if not settings.NESHAN_SERVICE_KEY:
            raise CommandError("NESHAN_SERVICE_KEY is empty.")
        if not services.refresh_provinces(force=True):
            raise CommandError("Neshan did not return the province list; nothing was changed.")

        failed = []
        for province in Province.objects.exclude(neshan_id=None):
            if not services.refresh_cities(province, force=True):
                failed.append(province.name)
            time.sleep(1)  # stay well under Neshan's per-minute limit

        unmatched = Province.objects.filter(neshan_id=None).count() + City.objects.filter(neshan_id=None).count()
        self.stdout.write(self.style.SUCCESS(f"{Province.objects.count()} provinces, {City.objects.count()} cities."))
        if unmatched:
            self.stdout.write(
                self.style.WARNING(f"{unmatched} row(s) are not in Neshan's lists (kept; review them in the admin).")
            )
        if failed:
            raise CommandError("Cities were not refreshed for: " + ", ".join(failed))
