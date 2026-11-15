"""Root URL configuration for MAL MAL."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.generic import RedirectView

handler404 = "apps.core.views.custom_404_view"
handler500 = "apps.core.views.custom_500_view"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=staticfiles_storage.url("favicon/favicon.ico"),
            permanent=False,
        ),
        name="favicon",
    ),
    path("", include("apps.core.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.search.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.cart.urls")),
    path("", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
    path("geo/", include("apps.geo.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
