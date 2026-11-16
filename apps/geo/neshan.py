"""Neshan Region API client (docs/vendors/neshan/neshan-region-api-guide.md).

Uses NESHAN_SERVICE_KEY, the same key as reverse geocoding. Returns [(neshan_id, name)].
"""

from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings

BASE_URL = "https://api.neshan.org/v2/region/provinces"
TIMEOUT = 4  # seconds; a customer may be waiting on this


class NeshanError(Exception):
    """Neshan could not be reached or answered with something unusable."""


def _get(url: str) -> list:
    request = Request(url, method="GET", headers={"Api-Key": settings.NESHAN_SERVICE_KEY, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8") or "[]")
    except (OSError, ValueError) as exc:  # URLError, HTTPError and timeouts are OSErrors
        raise NeshanError(f"HTTP {exc.code}" if isinstance(exc, HTTPError) else type(exc).__name__) from exc
    if not isinstance(data, list):
        raise NeshanError("unexpected response")
    return data


def _items(rows: list) -> list[tuple[int, str]]:
    items = [
        (row["id"], str(row["name"]).strip())
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), int) and str(row.get("name") or "").strip()
    ]
    if not items:
        raise NeshanError("no usable rows")
    return items


def fetch_provinces() -> list[tuple[int, str]]:
    return _items(_get(BASE_URL))


def fetch_cities(province_id: int) -> list[tuple[int, str]]:
    return _items(_get(f"{BASE_URL}/{int(province_id)}/cities"))
