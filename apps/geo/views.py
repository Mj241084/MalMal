"""Geo HTMX city options and Neshan reverse-geocoding proxy (docs/vendors/neshan/)."""

from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import caches
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.cache import safe_cache_get, safe_cache_set
from apps.core.text import normalize_fa
from apps.geo.models import City, Province

logger = logging.getLogger(__name__)

NESHAN_REVERSE_URL = "https://api.neshan.org/v5/reverse"
REVERSE_RATE_LIMIT = 30
REVERSE_RATE_WINDOW = 60
REVERSE_CACHE_TTL = 60 * 60


def _consume_reverse_quota(user_id: int) -> bool:
    rl = caches["ratelimit"]
    key = f"neshan:rev:u:{user_id}"
    try:
        rl.add(key, 0, REVERSE_RATE_WINDOW)
        count = rl.incr(key)
    except ValueError:
        rl.set(key, 1, REVERSE_RATE_WINDOW)
        count = 1
    return count <= REVERSE_RATE_LIMIT


def _match_province_and_city(state_raw: str | None, city_raw: str | None) -> tuple[int | None, int | None]:
    state_name = normalize_fa(state_raw or "").removeprefix("استان ").strip()
    city_name = normalize_fa(city_raw or "").strip()
    province = None
    if state_name:
        province = Province.objects.filter(name=state_name).first()
    city = None
    if province is not None and city_name:
        city = City.objects.filter(province=province, name=city_name).first()
    return (province.pk if province else None), (city.pk if city else None)


@require_GET
def city_options(request: HttpRequest) -> HttpResponse:
    province_id = request.GET.get("province") or ""
    cities = City.objects.none()
    if province_id.isdigit():
        cities = City.objects.filter(province_id=int(province_id)).only("id", "name")
    selected = request.GET.get("selected") or ""
    return render(
        request,
        "partials/_city_options.html",
        {"cities": cities, "selected": selected},
    )


@login_required
@require_GET
def reverse_geocode(request: HttpRequest) -> JsonResponse:
    if not settings.NESHAN_SERVICE_KEY:
        return JsonResponse({"enabled": False}, status=200)

    try:
        lat = float(request.GET.get("lat", ""))
        lng = float(request.GET.get("lng", ""))
    except ValueError:
        return JsonResponse({"error": "مختصات نامعتبر است"}, status=400)

    if not (24.0 <= lat <= 40.5 and 43.0 <= lng <= 64.0):
        return JsonResponse({"error": "مختصات خارج از محدوده‌ی ایران است"}, status=400)

    if not _consume_reverse_quota(request.user.pk):
        return JsonResponse({"error": "تعداد درخواست‌ها زیاد شد، کمی بعد تلاش کنید"}, status=429)

    cache_key = f"neshan:rev:{lat:.4f}:{lng:.4f}"
    cached = safe_cache_get(cache_key)
    if isinstance(cached, dict):
        return JsonResponse(cached)

    req = Request(
        f"{NESHAN_REVERSE_URL}?lat={lat:.6f}&lng={lng:.6f}",
        method="GET",
        headers={"Api-Key": settings.NESHAN_SERVICE_KEY, "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Neshan reverse geocode failed: %s", exc)
        return JsonResponse({"enabled": True, "error": "آدرس این نقطه دریافت نشد"}, status=502)

    if data.get("status") != "OK":
        return JsonResponse({"enabled": True, "error": "آدرس این نقطه پیدا نشد"}, status=422)

    province_id, city_id = _match_province_and_city(data.get("state"), data.get("city") or data.get("village"))
    payload = {
        "enabled": True,
        "address_text": normalize_fa(data.get("formatted_address") or ""),
        "province_id": province_id,
        "city_id": city_id,
    }
    safe_cache_set(cache_key, payload, REVERSE_CACHE_TTL)
    return JsonResponse(payload)
