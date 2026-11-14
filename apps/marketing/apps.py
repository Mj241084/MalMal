"""Marketing application: site-wide trust items (banners/collections land in P5)."""

from __future__ import annotations

from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.marketing"
    verbose_name = "بازاریابی"
