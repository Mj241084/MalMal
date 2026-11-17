"""Settings in the panel (docs/09 module 12): identity, invoice details, sales, advanced (superuser), shipping, gateways."""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod
from apps.panel.forms_settings import (
    AdvancedForm,
    GatewayForm,
    IdentityForm,
    LegalForm,
    SalesForm,
    ShippingMethodForm,
)
from apps.panel.permissions import panel_view
from apps.panel.views import common
from apps.payments.models import PaymentGateway

SITE, GATEWAY, SHIPPING = "core.change_sitesettings", "payments.change_paymentgateway", "orders.change_shippingmethod"
FORM = "panel/settings/form.html"
TITLES = {"identity": "هویت و تماس", "legal": "مشخصات فاکتور", "sales": "فروش", "advanced": "پیشرفته"}


@panel_view(any_of=(SITE, GATEWAY, SHIPPING))
@require_GET
def settings_index(request):
    for perm, name in (
        (SITE, "panel:settings_identity"),
        (SHIPPING, "panel:shipping_list"),
        (GATEWAY, "panel:gateway_list"),
    ):
        if request.user.has_perm(perm):
            return redirect(name)
    raise Http404


def _logos(site, form, request) -> None:
    for name in ("logo_light", "logo_dark"):
        if form.cleaned_data.get(f"{name}_clear") and not request.FILES.get(name):
            setattr(site, name, "")


def _site_tab(request, form_class, tab, prepare=None):
    site = SiteSettings.objects.get_or_create(pk=1)[0]  # not get_solo(): that one may be a cached copy
    return common.form_view(
        request, form_class, site, template=FORM, heading=TITLES[tab], back="panel:settings_index", noun="تنظیمات",
        prepare=prepare, after=lambda _obj: reverse(f"panel:settings_{tab}"), extra={"tab": tab},
    )  # fmt: skip


@panel_view(SITE)
@require_http_methods(["GET", "POST"])
def settings_identity(request):
    return _site_tab(request, IdentityForm, "identity", _logos)


@panel_view(SITE)
@require_http_methods(["GET", "POST"])
def settings_legal(request):
    return _site_tab(request, LegalForm, "legal")


@panel_view(SITE)
@require_http_methods(["GET", "POST"])
def settings_sales(request):
    return _site_tab(request, SalesForm, "sales")


@panel_view(superuser=True)
@require_http_methods(["GET", "POST"])
def settings_advanced(request):
    return _site_tab(request, AdvancedForm, "advanced")


# --- shipping methods --------------------------------------------------------


@panel_view(SHIPPING)
@require_GET
def shipping_list(request):
    return render(request, "panel/settings/shipping.html", {"methods": ShippingMethod.objects.all(), "tab": "shipping"})


@panel_view(SHIPPING)
@require_http_methods(["GET", "POST"])
def shipping_edit(request, pk):
    method = get_object_or_404(ShippingMethod, pk=pk)
    return common.form_view(
        request, ShippingMethodForm, method, template=FORM, heading="ویرایش روش ارسال", back="panel:shipping_list",
        noun="روش ارسال", extra={"tab": "shipping", "sub": True},
    )  # fmt: skip


# --- gateways ----------------------------------------------------------------


def _gateway_logo(gateway, form, request) -> None:
    if form.cleaned_data.get("logo_clear") and not request.FILES.get("logo"):
        gateway.logo = ""


@panel_view(GATEWAY)
@require_GET
def gateway_list(request):
    return render(
        request, "panel/settings/gateways.html", {"gateways": PaymentGateway.objects.all(), "tab": "gateways"}
    )


@panel_view(GATEWAY)
@require_http_methods(["GET", "POST"])
def gateway_edit(request, pk):
    gateway = get_object_or_404(PaymentGateway, pk=pk)
    return common.form_view(
        request, GatewayForm, gateway, template=FORM, heading="ویرایش درگاه", back="panel:gateway_list",
        noun="درگاه", prepare=_gateway_logo, extra={"tab": "gateways", "sub": True},
    )  # fmt: skip
