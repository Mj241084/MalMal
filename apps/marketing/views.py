"""Marketing views: collection list and collection detail (docs/02 §8)."""

from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET

from apps.catalog.filters import SORT_CHOICES, SORT_ORDERING, ProductFilter
from apps.marketing import services
from apps.marketing.models import Collection


@require_GET
def collection_list_view(request):
    context = {"collections": Collection.objects.live(), "breadcrumbs": [{"name": "مجموعه‌ها", "url": None}]}
    return render(request, "pages/collection_list.html", context)


@require_GET
def collection_view(request, slug):
    collection = get_object_or_404(Collection.objects.live(), slug=slug)  # inactive or outside its window = 404
    filters = ProductFilter.from_params(request.GET)
    explicit_sort = request.GET.get("sort") in SORT_ORDERING
    html = services.collection_results(collection, filters, explicit_sort)

    if request.htmx:
        response = HttpResponse(html)
        response["Cache-Control"] = "private, no-store"
        return response

    response = render(
        request,
        "pages/collection.html",
        {
            "collection": collection,
            "results_html": mark_safe(html),
            "filters": filters,
            "sort_choices": SORT_CHOICES,
            "sort_explicit": explicit_sort,
            "breadcrumbs": [
                {"name": "مجموعه‌ها", "url": "/collections/"},
                {"name": collection.title, "url": None},
            ],
            "canonical_url": request.build_absolute_uri(collection.get_absolute_url()),
        },
    )
    response["Cache-Control"] = "private, no-cache"
    return response
