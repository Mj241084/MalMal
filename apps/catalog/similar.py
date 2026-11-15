"""Similar products without a table (docs/03 §8). The view caches the rendered fragment."""

from __future__ import annotations

from collections import Counter

from apps.catalog.models import Category, Product, ProductSpecValue
from apps.catalog.tree import subtree_upper_bound

LIMIT = 12
POOL = 300
PRICE_BAND = 0.3


def base_category(product: Product) -> Category:
    """Candidates come from the parent's subtree (siblings included); a root category uses itself."""
    category = product.category
    return category.parent if category.parent_id else category


def similar_products(product: Product, limit: int = LIMIT) -> list[Product]:
    """Same leaf category +5, same brand +2, price within ±30% +2, +1 per shared filterable spec value."""
    base = base_category(product)
    pool = list(
        Product.objects.published()
        .filter(in_stock=True, category_path__gte=base.path, category_path__lt=subtree_upper_bound(base.path))
        .exclude(pk=product.pk)
        .with_list_relations()
        .order_by("-purchase_count_30d", "-pk")[:POOL]
    )
    if not pool:
        return []

    own = set(
        ProductSpecValue.objects.filter(product=product, attribute__is_filterable=True).values_list(
            "attribute_id", "value_text", "value_number"
        )
    )
    shared: Counter[int] = Counter()
    if own:
        rows = ProductSpecValue.objects.filter(
            product_id__in=[other.pk for other in pool], attribute__is_filterable=True
        ).values_list("product_id", "attribute_id", "value_text", "value_number")
        for product_id, *key in rows:
            if tuple(key) in own:
                shared[product_id] += 1

    low, high = product.min_price * (1 - PRICE_BAND), product.min_price * (1 + PRICE_BAND)

    def score(other: Product) -> int:
        points = 5 if other.category_id == product.category_id else 0
        if product.brand_id and other.brand_id == product.brand_id:
            points += 2
        if product.min_price and low <= other.min_price <= high:
            points += 2
        return points + shared[other.pk]

    return sorted(pool, key=lambda other: (-score(other), -other.purchase_count_30d, -other.pk))[:limit]
