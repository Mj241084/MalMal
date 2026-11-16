from __future__ import annotations

from django.apps import AppConfig


class PanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.panel"
    verbose_name = "پنل مدیریت"

    def ready(self) -> None:
        from apps.panel import providers  # noqa: F401  (registers search providers and navigation badges)
