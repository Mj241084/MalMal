"""Tests for core infrastructure: DB pragmas, Redis/env prod gates, icons, sprite, collectstatic, and views."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.core.cache import cache
from django.db import connection

from apps.core.apps import verify_sqlite_fts5
from apps.core.models import SiteSettings, StaticPage


@pytest.mark.django_db
class TestDatabaseAndInfrastructure:
    def test_sqlite_pragmas_and_fts5(self):
        verify_sqlite_fts5()
        with connection.cursor() as cursor:
            fk = cursor.execute("PRAGMA foreign_keys").fetchone()[0]
            bt = cursor.execute("PRAGMA busy_timeout").fetchone()[0]
            assert fk == 1
            assert bt == 5000
        assert connection.transaction_mode == "IMMEDIATE"

    def test_prod_settings_requires_secret_key_and_redis_url(self):
        base_env = {k: v for k, v in os.environ.items() if k not in ("DJANGO_SECRET_KEY", "REDIS_URL")}
        base_env["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"

        proc_missing_secret = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            env=base_env,
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR,
        )
        assert proc_missing_secret.returncode != 0
        assert "DJANGO_SECRET_KEY" in proc_missing_secret.stderr

        env_with_secret = {**base_env, "DJANGO_SECRET_KEY": "test-prod-secret-only"}
        proc_missing_redis = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            env=env_with_secret,
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR,
        )
        assert proc_missing_redis.returncode != 0
        assert "REDIS_URL" in proc_missing_redis.stderr

        # With only DJANGO_SECRET_KEY and REDIS_URL set, optional external env vars are non-blocking (D26).
        env_minimal_prod = {**env_with_secret, "REDIS_URL": "redis://127.0.0.1:6379/1"}
        proc_ok = subprocess.run(
            [sys.executable, "-c", "import django; django.setup(); print('PROD_OK')"],
            env=env_minimal_prod,
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR,
        )
        assert proc_ok.returncode == 0, proc_ok.stderr
        assert "PROD_OK" in proc_ok.stdout


@pytest.mark.django_db
class TestCoreModelsAndViews:
    def test_site_settings_singleton_and_cache_invalidation(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            s1 = SiteSettings.objects.create(store_name="مل‌مل", phone="02100000001")
            s2 = SiteSettings.objects.create(store_name="مل‌مل", phone="02100000002")
        assert s1.pk == 1
        assert s2.pk == 1
        assert SiteSettings.objects.count() == 1
        assert SiteSettings.get_solo().store_name == "مل‌مل"
        assert SiteSettings.get_solo().phone == "02100000002"

        cache.clear()
        assert SiteSettings.get_solo().store_name == "مل‌مل"
        assert SiteSettings.get_solo().phone == "02100000002"

    def test_home_has_no_external_cdn_and_inactive_pages_are_404(self, client, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            StaticPage.objects.create(slug="درباره-ما", title="درباره مل‌مل", body="متن تست", is_active=True)
            StaticPage.objects.create(slug="hidden", title="مخفی", body="...", is_active=False)

        res = client.get("/")
        assert res.status_code == 200
        body = res.content.decode("utf-8")
        # No external CDNs in rendered HTML
        assert "https://cdn." not in body
        assert "cdnjs.cloudflare.com" not in body
        assert "fonts.googleapis.com" not in body

        page_res = client.get("/pages/درباره-ما/")
        assert page_res.status_code == 200
        assert "درباره مل‌مل" in page_res.content.decode("utf-8")

        hidden_res = client.get("/pages/hidden/")
        assert hidden_res.status_code == 404
