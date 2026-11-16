from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.text import normalize_fa
from apps.panel import badges, nav, search
from apps.panel.permissions import panel_view


@panel_view(authenticated_only=True)
@require_GET
def search_view(request):
    query = request.GET.get("q", "")
    if len(normalize_fa(query)) < search.MIN_LENGTH:
        return HttpResponse("")
    return render(request, "panel/partials/search_results.html", {"results": search.search(request.user, query)})


@panel_view(authenticated_only=True)
@require_GET
def badges_view(request):
    """The sidebar again, polled every 60 s: fresh counters, active link from the page the poll came from."""
    path = (request.htmx.current_url_abs_path if request.htmx else "") or ""
    context = {
        "groups": nav.visible_groups(request.user, path),
        "counts": badges.counts_for(request.user),
        "request": request,
    }
    return render(request, "panel/partials/sidebar.html", context)
