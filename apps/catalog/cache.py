"""Versioned cache keys, single-flight rebuild, and invalidation (docs/03 §5).

Keys carry the database revision counters, so invalidation is a counter bump
instead of a delete: the old key simply stops being addressed and expires by TTL.
``rev`` / ``subtree_rev`` live in the database so a Redis flush cannot resurrect a
stale key.
"""

from __future__ import annotations

import hashlib
from typing import Any

from django.db.models import F

from apps.catalog.constants import (
    FRAGMENT_VERSION,
    LEVEL_LIST,
    TTL_CATEGORY_FACETS,
    TTL_CATEGORY_LIST,
    TTL_MENU,
    TTL_PRODUCT_CARD,
    TTL_PRODUCT_DETAIL,
    TTL_SEARCH_SUGGEST,
    TTL_SIMILAR,
)
from apps.core.cache import (
    get_or_build,
    read_epoch,
    safe_cache_incr_epoch,
)

# --- epoch -----------------------------------------------------------------


def current_epoch() -> int:
    """Global structural counter used by menu/home keys."""
    return read_epoch("epoch")


def bump_epoch() -> None:
    safe_cache_incr_epoch()


# --- key builders ----------------------------------------------------------


def product_detail_key(product) -> str:
    """Detail fragment key. Includes the site-wide trust-item revision so an admin
    edit of a TrustItem is not masked by a 12h product cache entry."""
    from apps.marketing.cache import trust_revision

    return f"p:{product.pk}:{product.rev}:t{trust_revision()}:v{FRAGMENT_VERSION}:detail"


def product_card_key(product) -> str:
    return f"p:{product.pk}:{product.rev}:v{FRAGMENT_VERSION}:card"


def category_list_key(category, sort: str, filters_hash: str, page: int) -> str:
    return f"c:{category.pk}:{category.subtree_rev}:v{FRAGMENT_VERSION}:list:{sort}:{filters_hash}:{page}"


def similar_key(product, base_category) -> str:
    """`base_category.subtree_rev` moves whenever any product in the candidate pool changes (LIST level)."""
    return f"p:{product.pk}:{product.rev}:{base_category.subtree_rev}:v{FRAGMENT_VERSION}:similar"


def category_facets_key(category) -> str:
    return f"c:{category.pk}:{category.subtree_rev}:facets"


def menu_key() -> str:
    return f"menu:{current_epoch()}"


def search_suggest_key(query: str) -> str:
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:16]
    return f"suggest:{current_epoch()}:{digest}"


def filters_hash(params: dict[str, Any]) -> str:
    parts = [f"{key}={params[key]}" for key in sorted(params) if params[key]]
    return hashlib.sha1("&".join(parts).encode("utf-8")).hexdigest()[:16]


# --- single-flight build ---------------------------------------------------
# ``get_or_build`` lives in apps.core.cache and is re-exported here for callers.


# --- invalidation ----------------------------------------------------------


def bump_product_rev(product_id: int) -> None:
    from apps.catalog.models import Product

    Product.objects.filter(pk=product_id).update(rev=F("rev") + 1)


def bump_subtree_rev(category_ids) -> None:
    from apps.catalog.models import Category

    ids = {int(cid) for cid in category_ids if cid}
    if not ids:
        return
    Category.objects.filter(pk__in=ids).update(subtree_rev=F("subtree_rev") + 1)


def _ancestor_ids(category_id: int | None) -> list[int]:
    if not category_id:
        return []
    from apps.catalog.models import Category
    from apps.catalog.tree import ancestor_ids

    path = Category.objects.filter(pk=category_id).values_list("path", flat=True).first()
    return ancestor_ids(path) if path else []


def invalidate_product(
    product_id: int,
    level: str,
    old_category_id: int | None = None,
    new_category_id: int | None = None,
) -> None:
    """Apply the invalidation level for a product change. Runs after commit."""
    bump_product_rev(product_id)

    if level == LEVEL_LIST:
        bump_subtree_rev(_ancestor_ids(old_category_id) + _ancestor_ids(new_category_id))
        bump_epoch()

    # The FTS row mirrors LIST fields; refresh it after the row is committed.
    from apps.search.index import reindex_product

    reindex_product(product_id)


def invalidate_category(category_id: int, old_path: str | None = None) -> None:
    """Structural category change: the subtree caches (of the old chain too, after a move) and the menu epoch move."""
    from apps.catalog.tree import ancestor_ids

    ids = _ancestor_ids(category_id)
    if old_path:
        ids += ancestor_ids(old_path)
    bump_subtree_rev(ids)
    bump_epoch()


def touch_product(product_id: int, level: str = LEVEL_LIST) -> None:
    """Invalidate a product (and its category chain) by id, for changes made outside Product.save()."""
    from apps.catalog.models import Product

    category_id = Product.objects.filter(pk=product_id).values_list("category_id", flat=True).first()
    if category_id is not None:
        invalidate_product(product_id, level, category_id, category_id)


def invalidate_brand(brand_id: int) -> None:
    from apps.catalog.models import Product
    from apps.catalog.search_text import build_search_text

    for product in Product.objects.filter(brand_id=brand_id).select_related("brand", "category"):
        text = build_search_text(product)
        if text != product.search_text:
            Product.objects.filter(pk=product.pk).update(search_text=text)  # allowed file (architecture test)
        invalidate_product(product.pk, LEVEL_LIST, product.category_id, product.category_id)


def invalidate_menu() -> None:
    bump_epoch()


# Re-exported TTLs so views import from one place.
__all__ = [
    "TTL_CATEGORY_FACETS",
    "TTL_CATEGORY_LIST",
    "TTL_MENU",
    "TTL_PRODUCT_CARD",
    "TTL_PRODUCT_DETAIL",
    "TTL_SEARCH_SUGGEST",
    "TTL_SIMILAR",
    "bump_epoch",
    "bump_product_rev",
    "bump_subtree_rev",
    "category_facets_key",
    "category_list_key",
    "current_epoch",
    "filters_hash",
    "get_or_build",
    "invalidate_brand",
    "invalidate_category",
    "invalidate_menu",
    "invalidate_product",
    "menu_key",
    "product_card_key",
    "product_detail_key",
    "search_suggest_key",
    "similar_key",
    "touch_product",
]
