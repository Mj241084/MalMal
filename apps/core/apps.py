"""Core application configuration and startup checks."""

from __future__ import annotations

import sqlite3

from django.apps import AppConfig
from django.contrib.staticfiles.apps import StaticFilesConfig
from django.core.exceptions import ImproperlyConfigured


class MalmalStaticFilesConfig(StaticFilesConfig):
    """Exclude source assets under static/src/ from collectstatic."""

    ignore_patterns = ["CVS", ".*", "*~", "src", "src/*"]


def verify_sqlite_fts5() -> None:
    """Fail fast at startup if the Python SQLite build lacks FTS5."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts5_probe USING fts5(x)")
    except sqlite3.OperationalError as exc:
        raise ImproperlyConfigured(
            "SQLite FTS5 extension is required but unavailable in this Python/SQLite build."
        ) from exc
    finally:
        conn.close()


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "هسته سایت"

    def ready(self) -> None:
        verify_sqlite_fts5()
