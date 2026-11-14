"""FTS5 index maintenance and query helpers (docs/03 §7).

Ranking uses ``bm25``. SQLite requires one weight per column, so the UNINDEXED
``product_id`` column takes 0 and the documented weights follow:
title 10, brand 5, category 3, model_codes 8, tokens 1.
"""

from __future__ import annotations

import logging
import sqlite3

from django.db import connection

from apps.core.text import normalize_fa

logger = logging.getLogger(__name__)

BM25_WEIGHTS = (0.0, 10.0, 5.0, 3.0, 8.0, 1.0)


def _fts_available() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product_fts'")
        return cursor.fetchone() is not None


def _row_for(product) -> tuple:
    from apps.catalog.search_text import model_code_variants

    brand = product.brand
    brand_text = " ".join(filter(None, [brand.name_fa, brand.name_en, brand.aliases])) if brand else ""
    category = product.category
    category_text = " ".join([category.name, *(ancestor.name for ancestor in category.ancestors())]) if category else ""

    codes: list[str] = []
    if product.pk:
        for sku in product.variants.values_list("sku", flat=True):
            codes.extend(model_code_variants(sku))
    model_codes = " ".join(codes)

    return (
        product.pk,
        normalize_fa(product.title, for_search=True),
        normalize_fa(brand_text, for_search=True),
        normalize_fa(category_text, for_search=True),
        normalize_fa(model_codes, for_search=True),
        product.search_text or "",
    )


def reindex_product(product_id: int) -> None:
    """Replace the FTS row for one product; inactive or missing products are removed."""
    from apps.catalog.models import Product

    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM product_fts WHERE product_id = %s", [product_id])
            product = (
                Product.objects.filter(pk=product_id, status=Product.STATUS_ACTIVE)
                .select_related("brand", "category")
                .first()
            )
            if product is None:
                return
            cursor.execute(
                "INSERT INTO product_fts (product_id, title, brand, category, model_codes, tokens) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                _row_for(product),
            )
    except sqlite3.OperationalError:  # pragma: no cover - index not migrated yet
        logger.warning("FTS index unavailable; skipped reindex for product %s", product_id)


def rebuild_all() -> int:
    """Drop and refill the whole index. Idempotent; used by ``rebuild_search``."""
    from apps.catalog.models import Product

    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM product_fts")
        count = 0
        products = Product.objects.filter(status=Product.STATUS_ACTIVE).select_related("brand", "category")
        for product in products.iterator(chunk_size=200):
            cursor.execute(
                "INSERT INTO product_fts (product_id, title, brand, category, model_codes, tokens) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                _row_for(product),
            )
            count += 1
    return count


def _match_expression(query: str) -> str:
    """Quote each term and turn the last one into a prefix query."""
    terms = [term for term in normalize_fa(query, for_search=True).split() if term]
    if not terms:
        return ""
    quoted = [f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms]
    quoted[-1] = f"{quoted[-1]}*"
    return " ".join(quoted)


def search_product_ids(query: str, limit: int = 24) -> list[int]:
    """Return active product ids ordered by relevance; falls back to LIKE."""
    expression = _match_expression(query)
    if not expression:
        return []

    ids: list[int] = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT product_id FROM product_fts WHERE product_fts MATCH %s "
                "ORDER BY bm25(product_fts, %s, %s, %s, %s, %s, %s) LIMIT %s",
                [expression, *BM25_WEIGHTS, limit],
            )
            ids = [int(row[0]) for row in cursor.fetchall()]
    except sqlite3.OperationalError:  # pragma: no cover - malformed query / index missing
        logger.warning("FTS query failed for %r", query)
        ids = []

    if ids:
        return ids
    return _like_fallback(query, limit)


def _like_fallback(query: str, limit: int) -> list[int]:
    from apps.catalog.models import Product

    normalized = normalize_fa(query, for_search=True)
    if not normalized:
        return []
    return list(
        Product.objects.filter(status=Product.STATUS_ACTIVE, search_text__contains=normalized)
        .order_by("-purchase_count_30d", "-created_at")
        .values_list("pk", flat=True)[:limit]
    )


def suggest_categories(query: str, limit: int = 3):
    """Category suggestions for the live search box."""
    from apps.catalog.models import Category

    normalized = normalize_fa(query, for_search=True)
    if not normalized:
        return []
    matches = []
    for category in Category.objects.filter(is_active=True).only("id", "name", "slug", "path")[:500]:
        if normalized in normalize_fa(category.name, for_search=True):
            matches.append(category)
            if len(matches) >= limit:
                break
    return matches
