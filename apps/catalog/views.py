"""Catalog views: category listing, product detail, brand listing, variant panel."""

from __future__ import annotations

import json

from django.db.models import Count, Max, Min
from django.http import Http404, HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET

from apps.catalog.cache import (
    TTL_CATEGORY_FACETS,
    TTL_CATEGORY_LIST,
    TTL_PRODUCT_DETAIL,
    TTL_SIMILAR,
    category_facets_key,
    category_list_key,
    get_or_build,
    product_detail_key,
    similar_key,
)
from apps.catalog.filters import PAGE_SIZE, SORT_CHOICES, ProductFilter
from apps.catalog.models import Brand, Category, Product, SpecAttribute, Variant
from apps.catalog.similar import base_category, similar_products
from apps.catalog.tree import subtree_upper_bound
from apps.core.html import sanitize_html
from apps.core.models import SiteSettings


def _crumbs(*items) -> list[dict]:
    """Breadcrumb dicts; the last item is rendered as plain text."""
    crumbs = []
    for index, item in enumerate(items):
        is_last = index == len(items) - 1
        crumbs.append(
            {
                "name": getattr(item, "name", None) or getattr(item, "title", ""),
                "url": None if is_last else item.get_absolute_url(),
            }
        )
    return crumbs


def _subtree_products(category: Category):
    """Products of the category and all descendants, using the path range."""
    return Product.objects.filter(
        status=Product.STATUS_ACTIVE,
        category_path__gte=category.path,
        category_path__lt=subtree_upper_bound(category.path),
    )


def _build_facets(category: Category) -> dict:
    products = _subtree_products(category)

    brands = list(
        products.exclude(brand__isnull=True)
        .values("brand_id", "brand__name_fa", "brand__slug")
        .annotate(count=Count("pk"))
        .order_by("-count", "brand__name_fa")
    )
    price_range = products.aggregate(low=Min("min_price"), high=Max("max_price"))

    attributes = []
    subtree_categories = category.descendants().values_list("pk", flat=True)
    for attribute in SpecAttribute.objects.filter(category_id__in=subtree_categories, is_filterable=True).order_by(
        "sort", "pk"
    ):
        values = (
            attribute.values.filter(product__in=products)
            .exclude(value_text="")
            .values("value_text")
            .annotate(count=Count("pk"))
            .order_by("-count", "value_text")[:8]
        )
        values = [row["value_text"] for row in values if row["value_text"]]
        if values:
            attributes.append({"id": attribute.pk, "name": attribute.name, "values": values})

    return {
        "brands": [{"id": row["brand_id"], "name": row["brand__name_fa"], "count": row["count"]} for row in brands],
        "price_low": price_range["low"] or 0,
        "price_high": price_range["high"] or 0,
        "attributes": attributes,
    }


def _render_results(category: Category, filters: ProductFilter) -> str:
    from django.core.paginator import Paginator

    queryset = filters.apply(_subtree_products(category).with_list_relations())
    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(filters.page)
    return render_to_string(
        "partials/_category_results.html",
        {
            "category": category,
            "page_obj": page_obj,
            "filters": filters,
            "total": paginator.count,
            "querystring": filters.querystring(),
        },
    )


def _viewer_tag(request: HttpRequest) -> str:
    return f"u{request.user.pk}" if request.user.is_authenticated else "u0"


@require_GET
def category_view(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    category = get_object_or_404(Category.objects.select_related("parent"), pk=pk, is_active=True)
    if slug != category.slug:
        return HttpResponsePermanentRedirect(category.get_absolute_url())

    filters = ProductFilter.from_params(request.GET)
    facets = get_or_build(category_facets_key(category), lambda: _build_facets(category), TTL_CATEGORY_FACETS)

    key = category_list_key(category, filters.sort, filters.cache_fragment(), filters.page)
    results_html = get_or_build(key, lambda: _render_results(category, filters), TTL_CATEGORY_LIST)

    if request.htmx:
        response = HttpResponse(results_html)
        response["Cache-Control"] = "private, no-store"
        return response

    children = list(category.children.filter(is_active=True).order_by("menu_order", "name"))

    response = render(
        request,
        "pages/category.html",
        {
            "category": category,
            "children": children,
            "breadcrumbs": _crumbs(*category.ancestors(), category),
            "facets": facets,
            "filters": filters,
            "sort_choices": SORT_CHOICES,
            "results_html": mark_safe(results_html),
            "canonical_url": request.build_absolute_uri(category.get_absolute_url()),
        },
    )
    response["ETag"] = (
        f'"{category.pk}-{category.subtree_rev}-{filters.cache_fragment()}-{filters.page}-{_viewer_tag(request)}"'
    )
    response["Cache-Control"] = "private, no-cache"
    return response


def _product_context(product: Product) -> dict:
    from apps.marketing.cache import trust_items
    from apps.orders.shipping import product_page_note

    images = list(product.images.all())
    variants = list(product.variants.filter(is_active=True))
    default_variant = variants[0] if variants else None
    specs = list(product.spec_values.select_related("attribute").order_by("attribute__sort", "attribute__pk"))
    return {
        "product": product,
        "images": images,
        "variants": variants,
        "default_variant": default_variant,
        "active_variant": default_variant,
        "specs": specs,
        "low_stock_threshold": SiteSettings.get_solo().low_stock_threshold,
        "shipping_note": product_page_note(),
        "trust_items": trust_items(limit=2),
        "description_html": sanitize_html(product.description),
        "breadcrumbs": _crumbs(*product.category.ancestors(), product.category, product),
    }


def _json_ld(product: Product, request: HttpRequest) -> str:
    """schema.org Product payload. Prices are Toman in the DB, Rial in IRR offers."""
    absolute_url = request.build_absolute_uri(product.get_absolute_url())
    data: dict = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.title,
        "description": product.short_description or product.title,
        "url": absolute_url,
        "offers": {
            "@type": "Offer",
            "priceCurrency": "IRR",
            "price": product.min_price * 10,
            "availability": "https://schema.org/InStock" if product.in_stock else "https://schema.org/OutOfStock",
            "url": absolute_url,
        },
    }
    if product.brand_id:
        data["brand"] = {"@type": "Brand", "name": product.brand.name_fa}
    if product.main_image:
        data["image"] = [request.build_absolute_uri(product.main_image.largest())]
    if product.review_count:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": float(product.rating_avg),
            "reviewCount": product.review_count,
        }
    return json.dumps(data, ensure_ascii=False)


@require_GET
def product_view(request: HttpRequest, pk: int, slug: str) -> HttpResponse:
    product = get_object_or_404(
        Product.objects.select_related("brand", "category", "main_image"),
        pk=pk,
    )
    if slug != product.slug:
        return HttpResponsePermanentRedirect(product.get_absolute_url())
    if product.status != Product.STATUS_ACTIVE and not request.user.is_staff:
        raise Http404()

    etag = f'"{product.pk}-{product.rev}-{product.review_count}-{product.rating_sum}-{_viewer_tag(request)}"'
    if request.headers.get("If-None-Match") == etag:
        response = HttpResponse(status=304)
        response["ETag"] = etag
        response["Cache-Control"] = "private, no-cache"
        return response

    detail_html = get_or_build(product_detail_key(product), lambda: _render_detail(product), TTL_PRODUCT_DETAIL)

    response = render(
        request,
        "pages/product.html",
        {
            **_product_context(product),
            "detail_html": mark_safe(detail_html),
            "canonical_url": request.build_absolute_uri(product.get_absolute_url()),
            "meta_title": product.seo_title or product.title,
            "meta_description": product.seo_description or product.short_description,
            "json_ld": _json_ld(product, request),
        },
    )
    response["ETag"] = etag
    response["Cache-Control"] = "private, no-cache"
    return response


def _render_detail(product: Product) -> str:
    return render_to_string("partials/_product_detail.html", _product_context(product))


@require_GET
def similar_view(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product.objects.select_related("category__parent"), pk=pk)
    if not product.is_active and not request.user.is_staff:
        raise Http404()
    html = get_or_build(
        similar_key(product, base_category(product)),
        lambda: render_to_string("partials/_similar.html", {"products": similar_products(product)}),
        TTL_SIMILAR,
    )
    response = HttpResponse(html)
    response["Cache-Control"] = "private, max-age=300"
    return response


@require_GET
def variant_panel_view(request: HttpRequest, pk: int, variant_id: int) -> HttpResponse:
    from apps.marketing.cache import trust_items
    from apps.orders.shipping import product_page_note

    product = get_object_or_404(Product.objects.select_related("brand", "category"), pk=pk)
    variant = get_object_or_404(Variant, pk=variant_id, product=product, is_active=True)
    response = render(
        request,
        "partials/_variant_panel.html",
        {
            "product": product,
            "variants": list(product.variants.filter(is_active=True)),
            "active_variant": variant,
            "low_stock_threshold": SiteSettings.get_solo().low_stock_threshold,
            "shipping_note": product_page_note(),
            "trust_items": trust_items(limit=2),
        },
    )
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def brand_view(request: HttpRequest, slug: str) -> HttpResponse:
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    filters = ProductFilter.from_params(request.GET)
    queryset = filters.apply(Product.objects.filter(status=Product.STATUS_ACTIVE, brand=brand).with_list_relations())

    from django.core.paginator import Paginator

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(filters.page)

    response = render(
        request,
        "pages/brand.html",
        {
            "brand": brand,
            "page_obj": page_obj,
            "filters": filters,
            "sort_choices": SORT_CHOICES,
            "total": paginator.count,
            "breadcrumbs": _crumbs(brand),
            "canonical_url": request.build_absolute_uri(),
        },
    )
    response["Cache-Control"] = "private, no-cache"
    return response
