"""Brands in the panel (docs/09 module 6). The form lives in one shared modal."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_htmx.http import reswap, retarget

from apps.catalog.cache import invalidate_brand
from apps.catalog.models import Brand, Product
from apps.panel import audit, htmx
from apps.panel.forms_catalog import BrandForm
from apps.panel.permissions import panel_view

VIEW = "catalog.view_brand"


def _list_context(user) -> dict:
    brands = Brand.objects.annotate(
        product_total=Count("products", distinct=True),
        live_products=Count("products", filter=Q(products__status=Product.STATUS_ACTIVE), distinct=True),
    ).order_by("name_fa")
    return {
        "brands": list(brands),
        "can_change": user.has_perm("catalog.change_brand"),
        "can_delete": user.has_perm("catalog.delete_brand"),
    }


@panel_view(VIEW)
@require_GET
def brand_list(request):
    context = _list_context(request.user)
    context["can_add"] = request.user.has_perm("catalog.add_brand")
    return render(request, "panel/brands/list.html", context)


def _form_view(request, brand):
    form = BrandForm(request.POST or None, request.FILES or None, instance=brand)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if form.cleaned_data["logo_clear"] and not request.FILES.get("logo"):
            saved.logo = ""
        with transaction.atomic():
            saved.save()
            if brand is not None:  # alias and name changes must reach every product's search text
                transaction.on_commit(lambda: invalidate_brand(saved.pk), robust=True)
        audit.log(request.user, saved, audit.CHANGE if brand else audit.ADDITION, "ذخیره‌ی برند")
        response = render(request, "panel/brands/_list_results.html", _list_context(request.user))
        htmx.toast(response, "برند ذخیره شد")
        return htmx.close_popover(response, "brand-modal")
    response = render(request, "panel/brands/_form.html", {"form": form, "brand": brand})
    if request.method == "POST":
        retarget(response, "#brand-modal-body")
        reswap(response, "innerHTML")
    return response


@panel_view(VIEW, "catalog.add_brand")
@require_http_methods(["GET", "POST"])
def brand_new(request):
    return _form_view(request, None)


@panel_view(VIEW, "catalog.change_brand")
@require_http_methods(["GET", "POST"])
def brand_edit(request, pk):
    return _form_view(request, get_object_or_404(Brand, pk=pk))


@panel_view(VIEW, "catalog.delete_brand")
@require_POST
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if brand.products.exists():
        htmx.flash(request, "این برند محصول دارد؛ به‌جای حذف، غیرفعالش کنید", "error")
    else:
        audit.log(request.user, brand, audit.DELETION, "حذف برند")
        brand.delete()
        htmx.flash(request, "برند حذف شد")
    return redirect("panel:brands")
