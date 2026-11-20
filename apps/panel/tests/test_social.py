"""The social tab: permission, refusal of foreign links, normalization, footer."""

import pytest
from django.urls import reverse

from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db


def test_social_tab_needs_permission_and_saves_normalized_links(
    staff_client, client, django_capture_on_commit_callbacks
):
    url = reverse("panel:settings_social")
    assert staff_client("orders.view_order").get(url).status_code == 403

    manager = staff_client("core.change_sitesettings", mobile="09129990101")
    assert manager.post(url, {"x_url": "https://evil.example/x"}).status_code == 200  # refused
    assert SiteSettings.get_solo().x_url == ""

    with django_capture_on_commit_callbacks(execute=True):
        assert manager.post(url, {"telegram_url": "t.me/malmal"}).status_code == 302
    assert SiteSettings.get_solo().telegram_url == "https://t.me/malmal"

    body = client.get("/").content.decode()
    assert 'href="https://t.me/malmal"' in body and "instagram.com" not in body
