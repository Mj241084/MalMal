"""Everything under /panel/ is private and never indexed (D44)."""

from __future__ import annotations

PANEL_PREFIX = "/panel/"


class PanelHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(PANEL_PREFIX):
            response["Cache-Control"] = "private, no-store"
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
