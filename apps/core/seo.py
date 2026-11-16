"""SEO: sitemap, robots.txt and JSON-LD (docs/02 §14). Absolute URLs always come from SITE_URL."""

from __future__ import annotations

import json
from types import SimpleNamespace
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.catalog.models import Brand, Category, Product
from apps.core.models import StaticPage
from apps.marketing.models import Collection


class _Base(Sitemap):
    def get_urls(self, page=1, site=None, protocol=None):
        parts = urlsplit(settings.SITE_URL)
        return super().get_urls(page=page, site=SimpleNamespace(domain=parts.netloc), protocol=parts.scheme)


class StaticViews(_Base):
    def items(self):
        return ["core:home", "marketing:collection_list"]

    def location(self, name):
        return reverse(name)


class Products(_Base):
    def items(self):
        return Product.objects.published().only("id", "slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class Categories(_Base):
    def items(self):
        return Category.objects.active().only("id", "slug", "updated_at")

    def lastmod(self, obj):
        return obj.updated_at


class Brands(_Base):
    def items(self):
        return Brand.objects.filter(is_active=True, products__status=Product.STATUS_ACTIVE).distinct()

    def location(self, obj):
        return reverse("catalog:brand", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


class Collections(_Base):
    def items(self):
        return Collection.objects.live()

    def lastmod(self, obj):
        return obj.updated_at


class Pages(_Base):
    def items(self):
        return StaticPage.objects.filter(is_active=True, needs_review=False)  # drafts stay reachable but unlisted

    def location(self, obj):
        return reverse("core:static_page", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViews,
    "products": Products,
    "categories": Categories,
    "brands": Brands,
    "collections": Collections,
    "pages": Pages,
}

PRIVATE_PATHS = (
    "/account/",
    "/auth/",`n    "/panel/",`n    "/panel/",
    "/login/",
    "/cart/",
    "/checkout/",
    "/orders/",
    "/payments/",
    "/geo/",
    "/likes/",
    "/social/",
    "/reviews/",
    "/similar/",
    "/search/suggest/",
    "/p/*/variant/",
    "/r/",
    "/_styleguide/",
)


@require_GET
@cache_control(public=True, max_age=3600)
def robots_view(request):
    if settings.DEBUG:  # a staging copy must never be indexed
        body = "User-agent: *\nDisallow: /\n"
    else:
        rules = "\n".join(f"Disallow: {path}" for path in PRIVATE_PATHS)
        body = f"User-agent: *\n{rules}\n\nSitemap: {settings.SITE_URL}/sitemap.xml\n"
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def dumps_ld(data: dict) -> str:
    """JSON for a ld+json <script>; `<`, `>` and `&` are escaped so stored text can never close the tag."""
    text = json.dumps(data, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def breadcrumb_ld(crumbs) -> str:
    items = [{"@type": "ListItem", "position": 1, "name": "خانه", "item": settings.SITE_URL + reverse("core:home")}]
    for position, crumb in enumerate(crumbs, start=2):
        entry = {"@type": "ListItem", "position": position, "name": crumb["name"]}
        if crumb["url"]:
            entry["item"] = settings.SITE_URL + crumb["url"]
        items.append(entry)
    return dumps_ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})


def organization_ld(site) -> str:
    logo = site.logo_light.url if site.logo_light else static("favicon/icon-512.png")
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site.store_name,
        "url": settings.SITE_URL + "/",
        "logo": settings.SITE_URL + logo,
    }
    if site.phone:
        data["contactPoint"] = {
            "@type": "ContactPoint",
            "telephone": site.phone,
            "contactType": "customer service",
            "availableLanguage": "fa",
        }
    same_as = [url for url in (site.instagram_url, site.telegram_url, site.whatsapp_url) if url]
    if same_as:
        data["sameAs"] = same_as
    return dumps_ld(data)
