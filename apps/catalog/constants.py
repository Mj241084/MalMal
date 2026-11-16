"""Cache invalidation field groups (docs/03-data-model.md §5).

Every tracked field belongs to exactly one group. The invalidation level of a
change is the highest level among the changed fields:

    LIST   -> product.rev++, ancestors' subtree_rev++, FTS rebuild, epoch++
    DETAIL -> product.rev++
    COUNTER-> nothing (F() writes, short TTL on social cache)
"""

from __future__ import annotations

LEVEL_LIST = "LIST"
LEVEL_DETAIL = "DETAIL"

# Fields visible in lists, cards and search results.
TRACKED_LIST = frozenset(
    {
        "title",
        "slug",
        "brand_id",
        "category_id",
        "status",
        "main_image_id",
        "min_price",
        "max_price",
        "compare_at_min",
        "discount_pct",
        "in_stock",
        "search_text",
    }
)

# Fields used only on the product detail page.
TRACKED_DETAIL = frozenset(
    {
        "short_description",
        "description",
        "warranty_text",
        "seo_title",
        "seo_description",
    }
)

# Variant fields that affect the product detail page (docs/03 §5, D29).
# price/compare_at_price/is_active/sort also move the LIST aggregates, so their level is decided by the aggregate diff.
VARIANT_DETAIL_FIELDS = frozenset(
    {"title", "options", "max_per_order", "price", "compare_at_price", "is_active", "sort"}
)

# Structural category fields: any change invalidates the menu and subtree caches.
CATEGORY_STRUCTURAL = frozenset(
    {
        "parent_id",
        "name",
        "slug",
        "logo",
        "description",
        "is_featured",
        "featured_order",
        "show_in_menu",
        "menu_order",
        "is_active",
        "spec_inherit",
    }
)

# Cache TTLs (seconds). A safety TTL keeps orphaned versioned keys from piling up.
TTL_PRODUCT_DETAIL = 60 * 60 * 12
TTL_PRODUCT_CARD = 60 * 60 * 12
TTL_CATEGORY_LIST = 60 * 60 * 6
TTL_CATEGORY_FACETS = 60 * 60 * 6
TTL_MENU = 60 * 60 * 24
TTL_SEARCH_SUGGEST = 60
# Bump when the markup of a cached fragment (product detail, cards, category results, similar rail) changes.
FRAGMENT_VERSION = 4
TTL_SIMILAR = 60 * 60 * 6

# Image renditions generated on upload.
IMAGE_WIDTHS = (400, 800, 1200)
