"""Core views: home shell, static pages, debug styleguide, and error pages."""

from __future__ import annotations

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.views.decorators.http import require_GET

from apps.core import shortlinks
from apps.core.models import SiteSettings, StaticPage


@require_GET
def home_view(request: HttpRequest) -> HttpResponse:
    from apps.core import seo
    from apps.marketing.services import home_context

    context = home_context()
    context["organization_ld"] = seo.organization_ld(SiteSettings.get_solo())
    return render(request, "pages/home.html", context)


@require_GET
def static_page_view(request: HttpRequest, slug: str) -> HttpResponse:
    page = get_object_or_404(StaticPage, slug=slug, is_active=True)
    return render(request, "pages/static_page.html", {"page": page})


@require_GET
def short_link_redirect_view(request: HttpRequest, code: str) -> HttpResponse:
    from django.apps import apps

    try:
        kind, pk = shortlinks.decode(code.lower())
    except ValueError:
        raise Http404 from None
    app_label, model_name = shortlinks.KINDS[kind]
    obj = apps.get_model(app_label, model_name).objects.filter(pk=pk).first()
    if obj is None or not getattr(obj, "is_active", True):
        raise Http404
    return redirect(obj.get_absolute_url())  # 302: the canonical URL may change


@require_GET
def styleguide_view(request: HttpRequest) -> HttpResponse:
    if not settings.DEBUG:
        raise Http404()

    sample_products = [
        {
            "title": "ماشین لباسشویی ۹ کیلویی بوش سری ۶ مدل WGA244X0IR",
            "brand": "بوش",
            "price": 46800000,
            "compare_at_price": 52000000,
            "discount_pct": 10,
            "in_stock": True,
            "liked": True,
        },
        {
            "title": "یخچال فریزر ساید بای ساید ۳۰ فوت اسنوا مدل SN8-2035GW",
            "brand": "اسنوا",
            "price": 68500000,
            "compare_at_price": None,
            "discount_pct": 0,
            "in_stock": True,
            "liked": False,
        },
        {
            "title": "جاروبرقی کیسه‌ای ۲۱۰۰ وات فیلیپس مدل FC9174",
            "brand": "فیلیپس",
            "price": 12450000,
            "compare_at_price": 13900000,
            "discount_pct": 10,
            "in_stock": True,
            "liked": False,
        },
        {
            "title": "چای‌ساز برقی ۱٫۷ لیتری تفال مدل BJ551B",
            "brand": "تفال",
            "price": 5900000,
            "compare_at_price": None,
            "discount_pct": 0,
            "in_stock": False,
            "liked": False,
        },
    ]

    statuses = [
        ("status-warning", "در انتظار پرداخت"),
        ("status-info", "پرداخت‌شده، در حال آماده‌سازی"),
        ("status-info", "ارسال‌شده"),
        ("status-success", "تحویل‌شده"),
        ("status-error", "لغو، پرداخت ناموفق"),
        ("status-neutral", "منقضی، بازگشت وجه"),
    ]

    return render(
        request,
        "pages/styleguide.html",
        {
            "sample_products": sample_products,
            "statuses": statuses,
        },
    )


@require_GET
def styleguide_ping_view(request: HttpRequest) -> HttpResponse:
    if not settings.DEBUG:
        raise Http404()
    return render(request, "partials/_styleguide_ping.html")


def custom_404_view(request: HttpRequest, exception=None) -> HttpResponse:
    return render(request, "404.html", status=404)


def custom_500_view(request: HttpRequest) -> HttpResponse:
    # No request context on purpose: the context processors need the database and Redis, which may be what failed.
    return HttpResponse(loader.get_template("500.html").render({}), status=500)
