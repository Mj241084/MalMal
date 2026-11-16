"""Tests for Neshan reverse geocode proxy and Region API sync."""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.geo import neshan, services, views
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


def test_refresh_adopts_existing_rows_by_name_and_is_idempotent(settings, monkeypatch):
    settings.NESHAN_SERVICE_KEY = "test-service-key"
    old_province = Province.objects.create(name="لرستان", slug="lorestan")
    old_city = City.objects.create(province=old_province, name="خرم\u200cآباد", slug="khorramabad")
    monkeypatch.setattr(neshan, "fetch_provinces", lambda: [(3641, "استان لرستان")])
    monkeypatch.setattr(neshan, "fetch_cities", lambda province_id: [(1063, "خرم آباد"), (1084, "بروجرد")])

    for _ in range(2):
        assert services.refresh_provinces(force=True)
        assert services.refresh_cities(Province.objects.get(), force=True)

    old_province.refresh_from_db()
    old_city.refresh_from_db()
    assert old_province.neshan_id == 3641
    assert old_city.neshan_id == 1063
    assert (Province.objects.count(), City.objects.count()) == (1, 2)  # adopted, never duplicated


def test_neshan_is_asked_once_per_cache_window(settings, monkeypatch):
    settings.NESHAN_SERVICE_KEY = "test-service-key"
    calls = []

    def fetch():
        calls.append(1)
        return [(3641, "استان لرستان")]

    monkeypatch.setattr(neshan, "fetch_provinces", fetch)

    services.refresh_provinces()
    services.refresh_provinces()

    assert len(calls) == 1
    assert Province.objects.get().neshan_id == 3641


def test_city_options_fall_back_to_the_database_when_neshan_is_down(client, settings, monkeypatch, province, city):
    settings.NESHAN_SERVICE_KEY = "test-service-key"
    Province.objects.filter(pk=province.pk).update(neshan_id=3641)
    calls = []

    def down(province_id):
        calls.append(province_id)
        raise neshan.NeshanError("timeout")

    monkeypatch.setattr(neshan, "fetch_cities", down)

    for _ in range(2):
        response = client.get(reverse("geo:city_options"), {"province": province.pk})
        assert response.status_code == 200
        assert city.name in response.content.decode()

    assert calls == [3641]  # the second request did not hit the failing service again
