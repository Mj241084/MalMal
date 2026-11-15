"""Seed the default home page block order so a fresh install has a real home page."""

from django.db import migrations

ROWS = [  # kind, rail_source, limit
    ("hero", "", 12),
    ("categories", "", 8),
    ("banner_strip", "", 12),
    ("product_rail", "best_selling", 12),
    ("product_rail", "newest", 12),
    ("product_rail", "discounted", 12),
    ("brands", "", 12),
    ("trust", "", 4),
]


def seed(apps, schema_editor):
    HomeBlock = apps.get_model("marketing", "HomeBlock")
    if HomeBlock.objects.exists():
        return
    for position, (kind, source, limit) in enumerate(ROWS, start=1):
        HomeBlock.objects.create(kind=kind, rail_source=source, limit=limit, sort=position * 10, is_active=True)


class Migration(migrations.Migration):
    dependencies = [("marketing", "0003_collection_banner_homeblock_collectionitem")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
