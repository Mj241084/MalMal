from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import render

from apps.panel import badges, search
from apps.panel.permissions import panel_view


@panel_view(authenticated_only=True)
def search_view(request):
    q = request.GET.get("q", "")
    hits = search.search(request.user, q)
    return render(request, "panel/partials/search_results.html", {"results": hits})


@panel_view(authenticated_only=True)
def badges_view(request):
    return JsonResponse(badges.counts_for(request.user))
