from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.panel.permissions import panel_view


@panel_view(superuser=True)
@require_GET
def guide(request):
    return render(request, "panel/guide.html")
