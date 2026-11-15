"""Home page and collection assembly (docs/02 §8.1).

Heavy data is cached under the global catalog epoch. Banner and collection windows are NOT part
of any cache key: they ride along in the cached data and are checked against `now` on every
request, so something appears and disappears exactly on time without invalidating anything.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, When
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from apps.catalog.cache import current_epoch
from apps.catalog.constants import FRAGMENT_VERSION
from apps.catalog.filters import PAGE_SIZE, SORT_ORDERING
from apps.catalog.models import Brand, Category, Product
from apps.catalog.tree import subtree_upper_bound
from apps.core.cache import get_or_build
from apps.marketing.cache import trust_items
from apps.marketing.models import Banner, Collection, HomeBlock, in_window

CACHE_TTL = 60 * 15
DEFAULT_RAIL_LIMIT = 12
DEFAULT_TITLES = {
    HomeBlock.CATEGORIES: "دسته‌بندی‌های برتر",
    HomeBlock.BRANDS: "برندها",
    HomeBlock.SOURCE_BEST: "پرفروش‌ترین‌ها",
    HomeBlock.SOURCE_NEWEST: "جدیدترین‌ها",
    HomeBlock.SOURCE_DISCOUNTED: "تخفیف‌دارها",
}
RULE_ORDERING = {**SORT_ORDERING, "discount": ["-discount_pct", "-pk"]}


# --- collections ---------------------------------------------------------


def _subtree_q(paths) -> Q:
    condition = Q()
    for path in paths:
        condition |= Q(category_path__gte=path, category_path__lt=subtree_upper_bound(path))
    return condition


def _position_order(ids: list[int]):
    return Case(
        *[When(pk=pk, then=index) for index, pk in enumerate(ids)], default=len(ids), output_field=IntegerField()
    )


def collection_products(collection: Collection):
    """(queryset of published products, default ordering) for either mode."""
    base = Product.objects.published()
    if collection.mode == Collection.MODE_MANUAL:
        ids = list(collection.items.order_by("sort", "pk").values_list("product_id", flat=True))
        if not ids:
            return base.none(), []
        return base.filter(pk__in=ids), [_position_order(ids)]

    queryset = base
    if collection.only_in_stock:
        queryset = queryset.filter(in_stock=True)
    if collection.min_discount_pct:
        queryset = queryset.filter(discount_pct__gte=collection.min_discount_pct)
    if collection.min_price is not None:
        queryset = queryset.filter(max_price__gte=collection.min_price)
    if collection.max_price is not None:
        queryset = queryset.filter(min_price__lte=collection.max_price)
    brand_ids = list(collection.brands.values_list("pk", flat=True))
    if brand_ids:
        queryset = queryset.filter(brand_id__in=brand_ids)
    paths = list(collection.categories.values_list("path", flat=True))
    if paths:
        queryset = queryset.filter(_subtree_q(paths))
    return queryset, RULE_ORDERING[collection.sort_by]


def _render_collection_results(collection, filters, explicit_sort: bool) -> str:
    queryset, ordering = collection_products(collection)
    queryset = filters.apply(queryset) if explicit_sort else filters.apply_filters(queryset).order_by(*ordering)
    paginator = Paginator(queryset.with_list_relations(), PAGE_SIZE)
    return render_to_string(
        "partials/_category_results.html",
        {
            "page_obj": paginator.get_page(filters.page),
            "filters": filters,
            "total": paginator.count,
            "querystring": filters.querystring(),
        },
    )


def collection_results(collection, filters, explicit_sort: bool) -> str:
    sort = filters.sort if explicit_sort else "default"
    key = f"col:{collection.pk}:{current_epoch()}:v{FRAGMENT_VERSION}:list:{sort}:{filters.cache_fragment()}:{filters.page}"
    return get_or_build(key, lambda: _render_collection_results(collection, filters, explicit_sort), CACHE_TTL)


# --- home data (cached) --------------------------------------------------


def _view_all(block: HomeBlock) -> str:
    if block.kind == HomeBlock.COLLECTION_RAIL and block.collection:
        return block.collection.get_absolute_url()
    if block.kind == HomeBlock.PRODUCT_RAIL and block.category and block.category.is_active:
        params = {
            "best_selling": {"sort": "best_selling"},
            "newest": {"sort": "newest"},
            "discounted": {"discounted": 1},
        }
        query = params.get(block.rail_source)
        return f"{block.category.get_absolute_url()}?{urlencode(query)}" if query else ""
    return ""


def _resolve_target(banner: Banner):
    """(href, extra windows, usable). A banner whose target is gone is hidden, never left dead."""
    kind = banner.target_type
    if kind == Banner.TARGET_NONE:
        return "", [], True
    if kind == Banner.TARGET_URL:
        return banner.target_url, [], bool(banner.target_url)
    if kind == Banner.TARGET_PRODUCT:
        target = banner.target_product
        return (target.get_absolute_url(), [], True) if target and target.is_active else ("", [], False)
    if kind == Banner.TARGET_CATEGORY:
        target = banner.target_category
        return (target.get_absolute_url(), [], True) if target and target.is_active else ("", [], False)
    target = banner.target_collection
    if target and target.is_active:
        return target.get_absolute_url(), [(target.starts_at, target.ends_at)], True
    return "", [], False


def _banner_rows() -> list[dict]:
    rows = []
    banners = Banner.objects.filter(is_active=True).select_related(
        "target_product", "target_category", "target_collection"
    )
    for banner in banners.order_by("sort", "pk"):
        href, windows, usable = _resolve_target(banner)
        if not usable:
            continue
        rows.append(
            {
                "placement": banner.placement,
                "alt": banner.alt,
                "desktop": banner.image_desktop.url,
                "mobile": (banner.image_mobile or banner.image_desktop).url,
                "href": href,
                "windows": [(banner.starts_at, banner.ends_at), *windows],
            }
        )
    return rows


def _category_rows() -> list[dict]:
    categories = Category.objects.filter(is_active=True, is_featured=True).order_by("featured_order", "name")[:12]
    return [{"name": c.name, "url": c.get_absolute_url(), "logo": c.logo.url if c.logo else ""} for c in categories]


def _brand_rows() -> list[dict]:
    brands = (
        Brand.objects.filter(is_active=True)
        .exclude(logo="")
        .annotate(live_products=Count("products", filter=Q(products__status=Product.STATUS_ACTIVE)))
        .filter(live_products__gt=0)
        .order_by("name_fa")[:24]
    )
    return [{"name": b.name_fa, "url": reverse("catalog:brand", args=[b.slug]), "logo": b.logo.url} for b in brands]


def _build_data() -> dict:
    blocks, collections = [], {}
    rows = HomeBlock.objects.filter(is_active=True).select_related("collection", "category").order_by("sort", "pk")
    for block in rows:
        if block.collection is not None:
            c = block.collection
            collections[c.pk] = {"active": c.is_active, "starts_at": c.starts_at, "ends_at": c.ends_at}
        blocks.append(
            {
                "id": block.pk,
                "kind": block.kind,
                "title": block.title,
                "rail_source": block.rail_source,
                "limit": block.limit,
                "collection_id": block.collection_id,
                "category_path": block.category.path if block.category else "",
                "view_all": _view_all(block),
            }
        )
    return {
        "blocks": blocks,
        "collections": collections,
        "banners": _banner_rows(),
        "categories": _category_rows(),
        "brands": _brand_rows(),
    }


# --- rails ---------------------------------------------------------------


def _auto_rail(block: dict):
    queryset = Product.objects.published()
    if block["category_path"]:
        queryset = queryset.filter(_subtree_q([block["category_path"]]))
    source = block["rail_source"]
    if source == HomeBlock.SOURCE_BEST:  # only real purchases: no unverified «best seller» claim
        return queryset.filter(in_stock=True, purchase_count_30d__gt=0).order_by("-purchase_count_30d", "-pk")
    if source == HomeBlock.SOURCE_DISCOUNTED:
        return queryset.filter(in_stock=True, discount_pct__gt=0).order_by("-discount_pct", "-pk")
    return queryset.filter(in_stock=True).order_by("-created_at", "-pk")


def _render_rail(block: dict) -> str:
    if block["kind"] == HomeBlock.COLLECTION_RAIL:
        collection = Collection.objects.filter(pk=block["collection_id"]).first()
        if collection is None:
            return ""
        queryset, ordering = collection_products(collection)
        queryset = queryset.order_by(*ordering)
        title = block["title"] or collection.title
    else:
        queryset = _auto_rail(block)
        title = block["title"] or DEFAULT_TITLES.get(block["rail_source"], "")
    products = list(queryset.with_list_relations()[: block["limit"] or DEFAULT_RAIL_LIMIT])
    if not products:
        return ""
    return render_to_string(
        "partials/_product_rail.html",
        {
            "title": title,
            "products": products,
            "view_all_url": block["view_all"],
            "rail_id": f"home-rail-{block['id']}",
        },
    )


# --- home context --------------------------------------------------------


def _prepare_block(block: dict, data: dict, now, epoch: int):
    kind = block["kind"]
    if kind in (HomeBlock.HERO, HomeBlock.BANNER_STRIP):
        placement = Banner.PLACEMENT_HERO if kind == HomeBlock.HERO else Banner.PLACEMENT_STRIP
        banners = [
            b
            for b in data["banners"]
            if b["placement"] == placement and all(in_window(now, start, end) for start, end in b["windows"])
        ]
        return {"kind": kind, "banners": banners} if banners else None
    if kind in (HomeBlock.CATEGORIES, HomeBlock.BRANDS):
        items = data["categories" if kind == HomeBlock.CATEGORIES else "brands"][: block["limit"] or None]
        title = block["title"] or DEFAULT_TITLES[kind]
        return {"kind": "tiles", "title": title, "items": items} if items else None
    if kind == HomeBlock.TRUST:
        items = trust_items(limit=block["limit"] or 4)
        return {"kind": kind, "items": items} if items else None
    if kind == HomeBlock.COLLECTION_RAIL:
        window = data["collections"].get(block["collection_id"])
        if not window or not window["active"] or not in_window(now, window["starts_at"], window["ends_at"]):
            return None
    if kind in (HomeBlock.PRODUCT_RAIL, HomeBlock.COLLECTION_RAIL):
        key = f"home:rail:{epoch}:{block['id']}:v{FRAGMENT_VERSION}"
        html = get_or_build(key, lambda: _render_rail(block), CACHE_TTL)
        return {"kind": "rail", "html": mark_safe(html)} if html else None
    return None


def home_context(now=None) -> dict:
    now = now or timezone.now()
    epoch = current_epoch()
    data = get_or_build(f"home:data:{epoch}:v{FRAGMENT_VERSION}", _build_data, CACHE_TTL)
    prepared = (_prepare_block(block, data, now, epoch) for block in data["blocks"])
    return {"home_blocks": [item for item in prepared if item]}
