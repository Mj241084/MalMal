"""Consistent SQLite backup (docs/03 §1): online backup API, verification of the copy, retention."""

import shutil
import sqlite3
import subprocess
import time
from contextlib import closing
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

COUNTED = ("accounts_user", "catalog_product", "orders_order", "payments_payment")


class Command(BaseCommand):
    help = "Back up the database to BACKUP_DIR (outside the project), verify the copy, drop old copies."

    def add_arguments(self, parser):
        parser.add_argument("--keep-days", type=int, default=14)
        parser.add_argument("--with-media", action="store_true")

    def handle(self, *args, keep_days, with_media, **options):
        if not settings.BACKUP_DIR:
            raise CommandError("BACKUP_DIR is not set (a folder outside the project, ideally on another disk).")
        folder = Path(settings.BACKUP_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"db-{timezone.localtime():%Y%m%d-%H%M%S}.sqlite3"

        with (
            closing(sqlite3.connect(connection.settings_dict["NAME"])) as source,
            closing(sqlite3.connect(target)) as copy,
        ):
            source.backup(copy)

        with closing(sqlite3.connect(target)) as copy:
            if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                target.unlink()
                raise CommandError("The backup failed its integrity check and was removed.")
            counts = {table: copy.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in COUNTED}

        cutoff = time.time() - keep_days * 86400
        for old in folder.glob("db-*.sqlite3"):
            if old != target and old.stat().st_mtime < cutoff:
                old.unlink()

        # cron does not read .env, so the media copy has to happen here instead of a crontab rsync line.
        if with_media and Path(settings.MEDIA_ROOT).is_dir():
            destination = folder / "media"
            destination.mkdir(parents=True, exist_ok=True)
            source = f"{settings.MEDIA_ROOT}/"
            if shutil.which("rsync"):
                try:
                    subprocess.run(["rsync", "-a", source, f"{destination}/"], check=True)
                except subprocess.CalledProcessError as exc:
                    raise CommandError(f"media sync failed: {exc}") from exc
            else:
                shutil.copytree(settings.MEDIA_ROOT, destination, dirs_exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f"{target.name} ok: " + ", ".join(f"{k}={v}" for k, v in counts.items())))
