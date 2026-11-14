"""Builds the normalized text blob that feeds the FTS5 index (docs/03 §7)."""

from __future__ import annotations

from apps.core.text import normalize_fa


def model_code_variants(value: str) -> list[str]:
    """Return the raw code plus a de-hyphenated form: ``WM-1234`` -> ``WM1234``."""
    raw = value.strip()
    if not raw:
        return []
    compact = "".join(ch for ch in raw if ch not in "-_/ ")
    return [raw] if compact == raw else [raw, compact]


def build_search_text(product) -> str:
    """Normalized search blob: title, brand names/aliases, category chain, model codes."""
    pieces: list[str] = [product.title or ""]

    if product.brand_id:
        brand = product.brand
        pieces.extend([brand.name_fa or "", brand.name_en or "", brand.aliases or ""])

    if product.category_id:
        pieces.append(product.category.name)
        pieces.append(" ".join(category.name for category in product.category.ancestors()))

    if product.short_description:
        pieces.append(product.short_description)

    if product.pk:
        for sku in product.variants.values_list("sku", flat=True):
            pieces.extend(model_code_variants(sku))
        for model in product.variants.values_list("options", flat=True):
            if isinstance(model, dict):
                pieces.extend(str(value) for value in model.values())

    return normalize_fa(" ".join(piece for piece in pieces if piece), for_search=True)
