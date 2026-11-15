"""Tests for core infrastructure: DB pragmas, Redis/env prod gates, icons, sprite, collectstatic, and views."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.template import Context, Template
from django.test import override_settings

from apps.core.apps import verify_sqlite_fts5
from apps.core.models import FooterLink, SiteSettings, StaticPage


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

    def test_collectstatic_ignores_src_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir, override_settings(STATIC_ROOT=tmpdir):
            call_command("collectstatic", "--noinput", verbosity=0)
            out = Path(tmpdir)
            assert (out / "css" / "app.css").is_file()
            assert (out / "sprite.svg").is_file()
            assert not (out / "src").exists()


@pytest.mark.django_db
class TestIconsAndSprite:
    def test_icon_tag_renders_stroke_1_5_and_rtl_flip(self):
        tpl = Template('{% load core_tags %}{% icon "chevron-left" flip=True size=20 class="text-ink-2" %}')
        html = tpl.render(Context())
        assert 'width="20"' in html
        assert 'stroke-width="1.5"' in html
        assert "rtl:-scale-x-100" in html
        assert "sprite.svg#chevron-left" in html

    @override_settings(DEBUG=True)
    def test_missing_icon_raises_in_debug(self):
        tpl = Template('{% load core_tags %}{% icon "does-not-exist-xyz" %}')
        with pytest.raises(ValueError, match="does-not-exist-xyz"):
            tpl.render(Context())

    @override_settings(DEBUG=False)
    def test_missing_icon_silent_in_prod(self):
        tpl = Template('{% load core_tags %}{% icon "does-not-exist-xyz" %}')
        assert tpl.render(Context()) == ""

    def test_built_sprite_contains_used_icons_without_hardcoded_stroke_width(self):
        sprite_path = Path(settings.BASE_DIR) / "static" / "sprite.svg"
        assert sprite_path.is_file()
        tree = ET.parse(sprite_path)
        symbols = {e.attrib["id"]: e for e in tree.getroot() if e.tag.split("}")[-1] == "symbol" and "id" in e.attrib}
        assert "search" in symbols
        assert "chevron-left" in symbols
        assert "stroke-width" not in symbols["search"].attrib


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

    def test_home_and_static_pages_and_favicon_redirect(self, client, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            FooterLink.objects.create(group=FooterLink.GROUP_ABOUT, title="درباره ما", url="/pages/about/", sort=1)
            StaticPage.objects.create(slug="درباره-ما", title="درباره مل‌مل", body="متن تست", is_active=True)
            StaticPage.objects.create(slug="hidden", title="مخفی", body="...", is_active=False)

        res = client.get("/")
        assert res.status_code == 200
        body = res.content.decode("utf-8")
        assert 'dir="rtl"' in body
        assert 'lang="fa"' in body
        assert "malmal.theme" in body
        assert "درباره ما" in body
        # No external CDNs in rendered HTML
        assert "https://cdn." not in body
        assert "cdnjs.cloudflare.com" not in body
        assert "fonts.googleapis.com" not in body

        page_res = client.get("/pages/درباره-ما/")
        assert page_res.status_code == 200
        assert "درباره مل‌مل" in page_res.content.decode("utf-8")

        hidden_res = client.get("/pages/hidden/")
        assert hidden_res.status_code == 404

        fav_res = client.get("/favicon.ico")
        assert fav_res.status_code == 302
        assert "favicon.ico" in fav_res["Location"]

    def test_styleguide_only_in_debug(self, client):
        with override_settings(DEBUG=False):
            res = client.get("/_styleguide/")
            assert res.status_code == 404
