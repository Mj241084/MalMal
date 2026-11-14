"""City select endpoint behavior (dependent province/city selects)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.geo.models import City

pytestmark = pytest.mark.django_db


def _get(client, **params):
    return client.get(reverse("geo:city_options"), params)


def test_without_a_province_asks_for_one(client):
    response = _get(client)

    body = response.content.decode()
    assert response.status_code == 200
    assert "ابتدا استان را انتخاب کنید" in body
    assert body.count("<option") == 1


def test_only_cities_of_the_requested_province_are_returned(client, province, city, other_city):
    response = _get(client, province=province.pk)

    body = response.content.decode()
    assert "انتخاب شهر" in body
    assert city.name in body
    assert other_city.name not in body


def test_selected_city_is_preserved(client, province, city):
    response = _get(client, province=province.pk, selected=city.pk)

    assert f'value="{city.pk}" selected' in response.content.decode()


def test_non_numeric_province_is_ignored(client, city):
    response = _get(client, province="tehran")

    body = response.content.decode()
    assert "ابتدا استان را انتخاب کنید" in body
    assert city.name not in body


def test_unknown_province_yields_an_empty_list(client, city):
    response = _get(client, province=999999)

    body = response.content.decode()
    assert "ابتدا استان را انتخاب کنید" in body
    assert city.name not in body


def test_cities_are_listed_alphabetically(client, province):
    City.objects.create(province=province, name="ورامین", slug="varamin")
    City.objects.create(province=province, name="اسلامشهر", slug="eslamshahr")

    response = _get(client, province=province.pk)

    body = response.content.decode()
    assert body.index("اسلامشهر") < body.index("ورامین")
