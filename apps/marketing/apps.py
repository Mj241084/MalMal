"""Marketing application: trust items, banners, collections and home page blocks."""

from __future__ import annotations

from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.marketing"
    verbose_name = "بازاریابی"

    def ready(self) -> None:
        from apps.marketing import signals  # noqa: F401
