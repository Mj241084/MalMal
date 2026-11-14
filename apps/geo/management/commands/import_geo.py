"""Import provinces and cities from the in-repo dataset (docs/02 §6)."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.core.text import normalize_fa
from apps.geo.models import City, Province

DEFAULT_PATH = Path(settings.BASE_DIR) / "data" / "iran-geo.json"


class Command(BaseCommand):
    help = "Import provinces and cities from data/iran-geo.json (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to the geo dataset JSON.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report the dataset without writing to the database.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"Dataset not found: {path}")

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            provinces = payload["provinces"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise CommandError(f"Invalid dataset: {exc}") from exc

        province_count = 0
        city_count = 0
        with transaction.atomic():
            for sort, entry in enumerate(provinces):
                name = normalize_fa(entry["name"])
                province = Province.objects.filter(name=name).first()
                if province is None:
                    province = Province.objects.create(
                        name=name,
                        slug=self._slug(Province, name, sort),
                        sort=sort,
                    )
                elif province.sort != sort:
                    province.sort = sort
                    province.save(update_fields=["sort"])
                province_count += 1
                for city_name in entry["cities"]:
                    city_name = normalize_fa(city_name)
                    if not city_name:
                        continue
                    existing = City.objects.filter(province=province, name=city_name).first()
                    if existing is not None:
                        city_count += 1
                        continue
                    City.objects.create(
                        province=province,
                        name=city_name,
                        slug=self._slug(City, city_name, 0, province=province),
                    )
                    city_count += 1

            if options["dry_run"]:
                transaction.set_rollback(True)

        prefix = "Validated" if options["dry_run"] else "Imported"
        self.stdout.write(self.style.SUCCESS(f"{prefix} {province_count} provinces and {city_count} cities."))

    @staticmethod
    def _slug(model, name: str, sort: int, province: Province | None = None) -> str:
        base = slugify(name, allow_unicode=True) or f"item-{sort}"
        candidate = base
        counter = 2
        queryset = model.objects.all()
        if province is not None:
            queryset = queryset.filter(province=province)
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate
