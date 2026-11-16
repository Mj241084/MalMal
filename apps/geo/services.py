"""Province and city lists (docs/02 §6).

Neshan's Region API is the source; our own tables are the persistent copy.
Reads always come from the database, so every address foreign key stays valid and the lists keep working when
Neshan is down. A cache marker records that a list was refreshed recently, so Neshan is asked at most once per
SYNC_TTL for each list, and not at all for a few minutes after a failure.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from apps.core.cache import safe_cache_get, safe_cache_set
from apps.core.text import normalize_fa
from apps.geo import neshan
from apps.geo.models import City, Province

logger = logging.getLogger(__name__)

SYNC_TTL = 60 * 60 * 24 * 7  # the lists change rarely; anything >= 1 day is fine
DOWN_TTL = 60 * 5
DOWN_KEY = "geo:neshan_down"
PROVINCE_PREFIX = "استان "


def name_key(value) -> str:
    """Comparison key: ی/ک, ZWNJ and the «استان» prefix must not make the same place look different."""
    return normalize_fa(value, for_search=True).removeprefix(PROVINCE_PREFIX).strip()


def _unique_slug(queryset, name: str) -> str:
    base = slugify(name, allow_unicode=True) or "item"
    slug, n = base, 2
    while queryset.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def _due(scope: str, force: bool) -> bool:
    if not settings.NESHAN_SERVICE_KEY:
        return False
    return force or not (safe_cache_get(f"geo:synced:{scope}") or safe_cache_get(DOWN_KEY))


def _fetch(call, *args):
    try:
        return call(*args)
    except neshan.NeshanError as exc:
        logger.warning("Neshan region request failed: %s", exc)
        safe_cache_set(DOWN_KEY, 1, DOWN_TTL)
        return None


def refresh_provinces(*, force: bool = False) -> bool:
    """Copy Neshan's province list into the database. True only when Neshan was asked and answered."""
    if not _due("provinces", force):
        return False
    items = _fetch(neshan.fetch_provinces)
    if items is None:
        return False
    _upsert_provinces(items)
    safe_cache_set("geo:synced:provinces", 1, SYNC_TTL)
    return True


def refresh_cities(province: Province, *, force: bool = False) -> bool:
    scope = f"cities:{province.pk}"
    if province.neshan_id is None or not _due(scope, force):
        return False
    items = _fetch(neshan.fetch_cities, province.neshan_id)
    if items is None:
        return False
    _upsert_cities(province, items)
    safe_cache_set(f"geo:synced:{scope}", 1, SYNC_TTL)
    return True


# The network call is already done when these run: no network inside a transaction.


@transaction.atomic
def _upsert_provinces(items: list[tuple[int, str]]) -> None:
    known = list(Province.objects.all())
    by_id = {p.neshan_id: p for p in known if p.neshan_id is not None}
    by_key = {name_key(p.name): p for p in known if p.neshan_id is None}  # old rows are adopted, not duplicated
    for neshan_id, raw in items:
        name = normalize_fa(raw).removeprefix(PROVINCE_PREFIX).strip()
        province = by_id.get(neshan_id) or by_key.pop(name_key(name), None)
        if province is None:
            Province.objects.create(neshan_id=neshan_id, name=name, slug=_unique_slug(Province.objects, name))
        elif (province.neshan_id, province.name) != (neshan_id, name):
            province.neshan_id, province.name = neshan_id, name
            province.save(update_fields=["neshan_id", "name"])


@transaction.atomic
def _upsert_cities(province: Province, items: list[tuple[int, str]]) -> None:
    siblings = City.objects.filter(province=province)
    known = list(siblings)
    by_id = {c.neshan_id: c for c in known if c.neshan_id is not None}
    by_key = {name_key(c.name): c for c in known if c.neshan_id is None}
    for neshan_id, raw in items:
        name = normalize_fa(raw)
        city = by_id.get(neshan_id) or by_key.pop(name_key(name), None)
        if city is None:
            City.objects.create(province=province, neshan_id=neshan_id, name=name, slug=_unique_slug(siblings, name))
        elif (city.neshan_id, city.name) != (neshan_id, name):
            city.neshan_id, city.name = neshan_id, name
            city.save(update_fields=["neshan_id", "name"])
