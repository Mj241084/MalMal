"""Root URL configuration for MAL MAL."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView

from apps.core import seo

handler404 = "apps.core.views.custom_404_view"
handler500 = "apps.core.views.custom_500_view"


class FaviconRedirect(RedirectView):
    """Look the manifest entry up per request: prod's manifest may not exist yet at import time."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return staticfiles_storage.url("favicon/favicon.ico")


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("favicon.ico", FaviconRedirect.as_view(), name="favicon"),
    path(
        "sitemap.xml",
        cache_control(public=True, max_age=3600)(sitemap),
        {"sitemaps": seo.SITEMAPS},
        name="sitemap",
    ),
    path("robots.txt", seo.robots_view, name="robots"),
    path("", include("apps.core.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.marketing.urls")),
    path("", include("apps.search.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.cart.urls")),
    path("", include("apps.orders.urls")),
    path("", include("apps.engagement.urls")),
    path("panel/", include("apps.panel.urls")),
    path("payments/", include("apps.payments.urls")),
    path("geo/", include("apps.geo.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
