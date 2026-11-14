"""Tests for Neshan reverse geocode proxy and import_geo command."""

from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.geo import views
from apps.geo.models import City, Province

pytestmark = pytest.mark.django_db


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_reverse_geocode_requires_login(client: Client):
    url = reverse("geo:reverse_geocode")
    response = client.get(f"{url}?lat=35.6892&lng=51.3890")
    assert response.status_code == 302
    assert "/login/" in response["Location"]


def test_reverse_geocode_disabled_when_no_service_key(client: Client, settings):
    user = User.objects.create_user("09121112233")
    client.force_login(user)
    settings.NESHAN_SERVICE_KEY = ""

    response = client.get(f"{reverse('geo:reverse_geocode')}?lat=35.6892&lng=51.3890")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}


def test_reverse_geocode_invalid_or_out_of_iran_coordinates(client: Client, settings):
    user = User.objects.create_user("09121112233")
    client.force_login(user)
    settings.NESHAN_SERVICE_KEY = "test-service-key"

    url = reverse("geo:reverse_geocode")

    # Invalid lat/lng
    assert client.get(f"{url}?lat=abc&lng=51.3890").status_code == 400

    # Outside Iran
    assert client.get(f"{url}?lat=10.0&lng=10.0").status_code == 400


def test_reverse_geocode_success_and_cached(client: Client, settings, monkeypatch, province, city):
    user = User.objects.create_user("09121112233")
    client.force_login(user)
    settings.NESHAN_SERVICE_KEY = "test-service-key"

    payload = {
        "status": "OK",
        "formatted_address": "تهران، میدان آزادی",
        "state": f"استان {province.name}",
        "city": city.name,
    }

    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        return _FakeResponse(payload)

    monkeypatch.setattr(views, "urlopen", fake_urlopen)

    url = reverse("geo:reverse_geocode")
    response = client.get(f"{url}?lat=35.6892&lng=51.3890")
    assert response.status_code == 200
    data = response.json()

    assert data["enabled"] is True
    assert data["address_text"] == "تهران، میدان آزادی"
    assert data["province_id"] == province.pk
    assert data["city_id"] == city.pk
    assert len(calls) == 1

    # Second request should be served from cache
    response2 = client.get(f"{url}?lat=35.6892&lng=51.3890")
    assert response2.status_code == 200
    assert response2.json() == data
    assert len(calls) == 1


def test_import_geo_is_idempotent(tmp_path):
    geo_file = tmp_path / "iran-geo.json"
    geo_data = {
        "provinces": [
            {
                "name": "تهران",
                "cities": ["تهران", "ری"],
            },
            {
                "name": "اصفهان",
                "cities": ["اصفهان", "کاشان"],
            },
        ]
    }
    geo_file.write_text(json.dumps(geo_data, ensure_ascii=False), encoding="utf-8")

    out = StringIO()
    call_command("import_geo", path=str(geo_file), stdout=out)
    assert Province.objects.count() == 2
    assert City.objects.count() == 4
    tehran = Province.objects.get(name="تهران")
    assert tehran.slug == "تهران"

    # Second run
    out2 = StringIO()
    call_command("import_geo", path=str(geo_file), stdout=out2)
    assert Province.objects.count() == 2
    assert City.objects.count() == 4
    tehran.refresh_from_db()
    assert tehran.slug == "تهران"  # must NOT become تهران-2
