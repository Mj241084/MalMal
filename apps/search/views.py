"""Search views: results page and live suggestions (docs/02 §10)."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, When
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET

from apps.catalog.cache import TTL_SEARCH_SUGGEST, get_or_build, search_suggest_key
from apps.catalog.filters import PAGE_SIZE, SORT_CHOICES, SORT_ORDERING, ProductFilter
from apps.catalog.menu import popular_categories
from apps.catalog.models import Product
from apps.core.text import normalize_fa
from apps.search.index import search_product_ids, suggest_categories

SUGGEST_PRODUCT_LIMIT = 6
SUGGEST_CATEGORY_LIMIT = 3
RESULT_ID_LIMIT = 600


def _relevance_order(ids: list[int]):
    return Case(
        *[When(pk=pk, then=index) for index, pk in enumerate(ids)],
        output_field=IntegerField(),
    )


@require_GET
def search_view(request: HttpRequest) -> HttpResponse:
    raw_query = request.GET.get("q", "").strip()
    query = normalize_fa(raw_query, for_search=True)
    filters = ProductFilter.from_params(request.GET, query=query)
    explicit_sort = request.GET.get("sort") in SORT_ORDERING

    ids = search_product_ids(query, limit=RESULT_ID_LIMIT) if query else []
    queryset = Product.objects.published().filter(pk__in=ids).with_list_relations()
    if explicit_sort:
        queryset = filters.apply(queryset)
    else:
        queryset = filters.apply_filters(queryset).order_by(_relevance_order(ids))

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(filters.page)
    context = {
        "query": query,
        "raw_query": raw_query,
        "page_obj": page_obj,
        "filters": filters,
        "sort_choices": SORT_CHOICES,
        "explicit_sort": explicit_sort,
        "total": paginator.count,
        "popular_categories": popular_categories() if query and not paginator.count else [],
        "breadcrumbs": [],
        "canonical_url": request.build_absolute_uri(),
    }
    response = render(request, "partials/_listing_results.html" if request.htmx else "pages/search.html", context)
    if request.htmx:
        response["Cache-Control"] = "private, no-store"
    return response


def _build_suggestions(query: str) -> str:
    ids = search_product_ids(query, limit=SUGGEST_PRODUCT_LIMIT)
    products = list(Product.objects.filter(pk__in=ids).with_list_relations())
    order = {pk: index for index, pk in enumerate(ids)}
    products.sort(key=lambda product: order.get(product.pk, 0))
    categories = suggest_categories(query, limit=SUGGEST_CATEGORY_LIMIT)

    return render_to_string(
        "partials/_search_suggest.html",
        {
            "query": query,
            "products": products,
            "categories": categories,
            "popular_categories": popular_categories() if not products and not categories else [],
        },
    )


@require_GET
def suggest_view(request: HttpRequest) -> HttpResponse:
    query = normalize_fa(request.GET.get("q", ""), for_search=True)
    if len(query) < 2:
        return HttpResponse("")

    html = get_or_build(search_suggest_key(query), lambda: _build_suggestions(query), TTL_SEARCH_SUGGEST)
    response = HttpResponse(mark_safe(html))
    response["Cache-Control"] = "private, max-age=60"
    return response
