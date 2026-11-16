from __future__ import annotations

from django.views.generic import TemplateView

from apps.panel.permissions import panel_view


class DashboardView(TemplateView):
    template_name = "panel/dashboard.html"

    @panel_view(authenticated_only=True)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
