"""Seed the four assumed trust claims (docs/02 §8.1).

They are marked ``is_placeholder=True`` because the wording is an assumption, not
something the owner confirmed. ``manage.py check_launch`` warns until they are
edited in the admin (P6).
"""

from __future__ import annotations

from django.db import migrations

ITEMS = [
    ("truck", "ارسال به سراسر کشور", "", 0),
    ("shield-check", "ضمانت اصالت و سلامت کالا", "", 1),
    ("lock", "پرداخت امن آنلاین", "", 2),
    ("phone", "پشتیبانی تلفنی", "", 3),
]


def create_items(apps, schema_editor):
    TrustItem = apps.get_model("marketing", "TrustItem")
    for icon, title, subtitle, sort in ITEMS:
        TrustItem.objects.get_or_create(
            title=title,
            defaults={
                "icon": icon,
                "subtitle": subtitle,
                "sort": sort,
                "is_placeholder": True,
                "is_active": True,
            },
        )


def remove_items(apps, schema_editor):
    TrustItem = apps.get_model("marketing", "TrustItem")
    TrustItem.objects.filter(title__in=[title for _, title, _, _ in ITEMS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("marketing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_items, remove_items),
    ]
