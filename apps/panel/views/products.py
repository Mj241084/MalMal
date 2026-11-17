"""Products in the panel: list, quick price edit, creation and the studio (docs/09 module 4).

Writes go through apps.catalog.services (save(), never a raw queryset update: D35). Every studio section answers
with its own partial plus out-of-band refreshes of the sections that depend on it.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django_htmx.http import reswap, retarget

from apps.catalog import publishing, services, specs
from apps.catalog.models import Brand, Category, Product, ProductSpecValue, Variant
from apps.catalog.tree import subtree_upper_bound
from apps.core.jalali import to_fa_digits
from apps.core.models import SiteSettings
from apps.core.text import normalize_fa
from apps.panel import audit, htmx, ordering
from apps.panel.forms_catalog import (
    ProductBasicsForm,
    ProductCreateForm,
    QuickPriceForm,
    SpecsForm,
    VariantForm,
    category_label,
)
from apps.panel.permissions import panel_view

PAGE_SIZE = 25
VIEW, CHANGE = "catalog.view_product", "catalog.change_product"
STOCK_FILTERS = (("in", "موجود"), ("low", "کم‌موجود"), ("out", "ناموجود"))
MESSAGES = {
    Product.STATUS_ACTIVE: "محصول فعال شد و در فروشگاه دیده می‌شود",
    Product.STATUS_DRAFT: "محصول به پیش‌نویس برگشت و از فروشگاه برداشته شد",
    Product.STATUS_ARCHIVED: "محصول بایگانی شد و از فروشگاه برداشته شد",
}
SECTIONS = {
    "basics": ("basics", "specs", "publish"),  # a category change swaps the specification fields
    "gallery": ("gallery", "publish"),
    "variants": ("variants", "publish"),
    "specs": ("specs", "publish"),
    "publish": ("publish",),
}


def _digit_id(raw) -> int | None:
    raw = str(raw or "")
    return int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= 12 else None


# --- list ------------------------------------------------------------------


def _list_context(params, user) -> dict:
    queryset = Product.objects.select_related("brand", "category", "main_image")
    text = normalize_fa(params.get("q", ""), for_search=True)[:60]
    if text:
        queryset = queryset.filter(
            Q(search_text__contains=text) | Q(pk__in=Variant.objects.filter(sku__icontains=text).values("product_id"))
        )
    category_id = _digit_id(params.get("category"))
    category = Category.objects.filter(pk=category_id).first() if category_id else None
    if category is not None:
        queryset = queryset.filter(
            category_path__gte=category.path, category_path__lt=subtree_upper_bound(category.path)
        )
    if brand_id := _digit_id(params.get("brand")):
        queryset = queryset.filter(brand_id=brand_id)
    if params.get("status") in dict(Product.STATUS_CHOICES):
        queryset = queryset.filter(status=params["status"])
    stock_filter, low = params.get("stock", ""), SiteSettings.get_solo().low_stock_threshold
    if stock_filter == "in":
        queryset = queryset.filter(total_stock__gt=low)
    elif stock_filter == "low":
        queryset = queryset.filter(total_stock__gt=0, total_stock__lte=low)
    elif stock_filter == "out":
        queryset = queryset.filter(total_stock__lte=0)

    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {key: params.get(key, "") for key in ("q", "category", "brand", "status", "stock") if params.get(key)}
    return {
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "filters": filters,
        "qs": urlencode(filters),
        "hidden": [("page", page_obj.number), *filters.items()],
        "can_change": user.has_perm(CHANGE),
        "can_price": user.has_perm("catalog.change_variant"),
    }


@panel_view(VIEW)
@require_GET
def product_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/products/_list_results.html", context)
    context.update(
        category_options=[(c.pk, category_label(c)) for c in Category.objects.order_by("path")],
        brand_options=list(Brand.objects.order_by("name_fa").values_list("pk", "name_fa")),
        status_choices=Product.STATUS_CHOICES,
        stock_filters=STOCK_FILTERS,
        selected={key: context["filters"].get(key, "") for key in ("category", "brand", "status", "stock")},
        can_add=request.user.has_perm("catalog.add_product"),
    )
    return render(request, "panel/products/list.html", context)


@panel_view(VIEW, CHANGE)
@require_POST
def product_bulk(request):
    target = {"activate": Product.STATUS_ACTIVE, "archive": Product.STATUS_ARCHIVED}.get(request.POST.get("action"))
    ids = [i for i in (_digit_id(v) for v in request.POST.getlist("product")[:100]) if i]
    if target is None or not ids:
        message, level = "محصولی انتخاب نشده است", "error"
    else:
        done, blocked = 0, []
        for product in Product.objects.filter(pk__in=ids):
            try:
                services.set_status(product, target)
            except services.PublishError:
                blocked.append(product.title)
            else:
                audit.log(request.user, product, audit.CHANGE, MESSAGES[target])
                done += 1
        message = to_fa_digits(f"{done} محصول تغییر کرد")
        if blocked:
            message += to_fa_digits(f"؛ {len(blocked)} مورد چک‌لیست انتشار را نگذراند: ") + "، ".join(blocked[:3])
        level = "success" if done and not blocked else "warning"
    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:products")
    response = render(request, "panel/products/_list_results.html", _list_context(request.POST, request.user))
    return htmx.toast(response, message, level)


@panel_view(VIEW, "catalog.change_variant")
@require_http_methods(["GET", "POST"])
def product_quick(request, pk):
    product = get_object_or_404(Product, pk=pk)
    variants = list(product.variants.order_by("sort", "pk"))
    form = QuickPriceForm(request.POST or None, variants=variants)
    if request.method == "POST" and form.is_valid():
        services.apply_quick_prices(variants, form)
        audit.log(request.user, product, audit.CHANGE, "ویرایش سریع قیمت")
        response = render(request, "panel/products/_list_results.html", _list_context(request.POST, request.user))
        htmx.toast(response, "قیمت ذخیره شد")
        return htmx.close_popover(response, "quick-modal")
    params = request.POST if request.method == "POST" else request.GET
    response = render(
        request,
        "panel/products/_quick_form.html",
        {
            "product": product,
            "rows": [(v, form[f"price_{v.pk}"], form[f"compare_{v.pk}"]) for v in variants],
            "hidden": [(k, v) for k, v in params.items() if k in ("page", "q", "category", "brand", "status", "stock")],
        },
    )
    if request.method == "POST":  # keep the modal open with its errors
        retarget(response, "#quick-body")
        reswap(response, "innerHTML")
    return response


# --- create ----------------------------------------------------------------


@panel_view(VIEW, "catalog.add_product")
@require_http_methods(["GET", "POST"])
def product_new(request):
    form = ProductCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        product = services.create_draft(data["title"], data["category"], data["brand"])
        audit.log(request.user, product, audit.ADDITION, "ساخت پیش‌نویس")
        htmx.flash(request, "پیش‌نویس ساخته شد؛ عکس، قیمت و مشخصات را کامل کنید")
        return redirect("panel:product_studio", pk=product.pk)
    return render(request, "panel/products/new.html", {"form": form})


# --- studio ----------------------------------------------------------------


def _load(pk: int) -> Product:
    return get_object_or_404(Product.objects.select_related("brand", "category", "main_image"), pk=pk)


def _studio_context(request, product: Product, **forms) -> dict:
    user = request.user
    variants = list(product.variants.order_by("sort", "pk"))
    attributes = list(specs.applicable_attributes(product.category))
    values = {v.attribute_id: v for v in product.spec_values.select_related("attribute")}
    suggestions = services.spec_suggestions(attributes)
    specs_form = forms.get("specs_form") or SpecsForm(attributes=attributes, values=values)
    errors, warnings = publishing.publish_checks(product)
    known = {a.pk for a in attributes}
    return {
        "product": product,
        "basics_form": forms.get("basics_form") or ProductBasicsForm(instance=product),
        "images": list(product.images.order_by("sort", "pk")),
        "max_images": services.MAX_IMAGES,
        "variants": variants,
        "variant_forms": [
            (
                v,
                forms.get(f"vf{v.pk}")
                or VariantForm(
                    initial=services.variant_initial(v), product=product, instance=v, auto_id=f"var{v.pk}_%s"
                ),
            )
            for v in variants
        ],
        "new_variant_form": forms.get("new_variant_form")
        or VariantForm(initial=services.new_variant_initial(product), product=product, auto_id="varnew_%s"),
        "spec_rows": [(a, specs_form[f"spec_{a.pk}"], suggestions.get(a.pk, [])) for a in attributes],
        "orphans": [v for key, v in values.items() if key not in known],
        "publish_errors": errors,
        "publish_warnings": warnings,
        "delete_block": services.delete_block_reason(product),
        "can_delete": user.has_perm("catalog.delete_product"),
        "can_stock": user.has_perm("catalog.adjust_stock"),
    }


def _studio_response(request, product, section, message="", level="success", **forms):
    product = _load(product.pk)  # a ModelForm mutates its instance while validating: always render fresh data
    if not request.htmx:
        if message:
            htmx.flash(request, message, level)
        if not forms:
            return redirect("panel:product_studio", pk=product.pk)
        return render(request, "panel/products/studio.html", _studio_context(request, product, **forms))
    context = _studio_context(request, product, **forms)
    html = "".join(
        render_to_string(f"panel/products/_sec_{name}.html", {**context, "oob": index > 0}, request)
        for index, name in enumerate(SECTIONS[section])
    )
    response = HttpResponse(html)
    return htmx.toast(response, message, level) if message else response


def _need(request, perm):
    return request.user.has_perm(perm)


@panel_view(VIEW, CHANGE)
@require_GET
def product_studio(request, pk):
    product = _load(pk)
    return render(request, "panel/products/studio.html", _studio_context(request, product))


@panel_view(VIEW, CHANGE)
@require_POST
def product_basics(request, pk):
    product = _load(pk)
    form = ProductBasicsForm(request.POST, instance=product)
    if not form.is_valid():
        return _studio_response(request, product, "basics", "اطلاعات را بررسی کنید", "error", basics_form=form)
    if services.save_basics(form):
        audit.log(request.user, product, audit.CHANGE, "ویرایش اطلاعات پایه")
    return _studio_response(request, product, "basics", "اطلاعات ذخیره شد")


@panel_view(VIEW, CHANGE)
@require_POST
def product_publish(request, pk):
    product = _load(pk)
    target = request.POST.get("to")
    if target not in MESSAGES:
        return _studio_response(request, product, "publish", "وضعیت نامعتبر است", "error")
    try:
        services.set_status(product, target)
    except services.CatalogError as exc:
        return _studio_response(request, product, "publish", str(exc), "error")
    audit.log(request.user, product, audit.CHANGE, MESSAGES[target])
    return _studio_response(request, product, "publish", MESSAGES[target])


@panel_view(VIEW, "catalog.delete_product")
@require_POST
def product_delete(request, pk):
    product = _load(pk)
    reason = services.delete_block_reason(product)
    if reason:
        htmx.flash(request, reason, "error")
        return redirect("panel:product_studio", pk=pk)
    audit.log(request.user, product, audit.DELETION, "حذف پیش‌نویس")
    services.delete_product(product)
    htmx.flash(request, "پیش‌نویس حذف شد")
    return redirect("panel:products")


# --- gallery ---------------------------------------------------------------


@panel_view(VIEW, "catalog.add_productimage")
@require_POST
def product_images(request, pk):
    product = _load(pk)
    added, errors, warnings = services.add_images(product, request.FILES.getlist("files"))
    if added:
        audit.log(request.user, product, audit.CHANGE, to_fa_digits(f"افزودن {added} تصویر"))
    if errors:
        message, level = "؛ ".join(errors[:2]), "error"
    elif warnings:
        message, level = warnings[0], "warning"
    else:
        message, level = (to_fa_digits(f"{added} تصویر اضافه شد") if added else ""), "success"
    return _studio_response(request, product, "gallery", message, level)


@panel_view(VIEW, "catalog.change_productimage")
@require_POST
def product_image_action(request, pk, image_pk, action):
    product = _load(pk)
    image = get_object_or_404(product.images, pk=image_pk)
    if action == "alt":
        services.set_image_alt(image, request.POST.get("alt", ""))
        return HttpResponse(status=204)
    if action in ("up", "down", "first"):
        with transaction.atomic():
            if ordering.reorder(list(product.images.order_by("sort", "pk")), image.pk, action):
                publishing.sync_main_image(product)
        return _studio_response(request, product, "gallery")
    if action == "delete":
        if not _need(request, "catalog.delete_productimage"):
            return _studio_response(request, product, "gallery", "اجازه‌ی حذف تصویر را ندارید", "error")
        services.delete_image(product, image)
        audit.log(request.user, product, audit.CHANGE, "حذف تصویر")
        return _studio_response(request, product, "gallery", "تصویر حذف شد")
    return _studio_response(request, product, "gallery", "عمل نامعتبر است", "error")


# --- variants --------------------------------------------------------------


@panel_view(VIEW, "catalog.add_variant")
@require_POST
def variant_new(request, pk):
    product = _load(pk)
    form = VariantForm(request.POST, product=product, auto_id="varnew_%s")
    if not form.is_valid():
        return _studio_response(
            request, product, "variants", "اطلاعات تنوع را بررسی کنید", "error", new_variant_form=form
        )
    try:
        variant = services.save_variant(product, form, by=request.user)
    except services.CatalogError as exc:
        return _studio_response(request, product, "variants", str(exc), "error", new_variant_form=form)
    audit.log(request.user, product, audit.CHANGE, f"افزودن تنوع {variant.sku}")
    return _studio_response(request, product, "variants", "تنوع اضافه شد")


@panel_view(VIEW, "catalog.change_variant")
@require_POST
def variant_edit(request, pk, variant_pk):
    product = _load(pk)
    variant = get_object_or_404(product.variants, pk=variant_pk)
    form = VariantForm(request.POST, product=product, instance=variant, auto_id=f"var{variant.pk}_%s")
    key = f"vf{variant.pk}"
    if not form.is_valid():
        return _studio_response(request, product, "variants", "اطلاعات تنوع را بررسی کنید", "error", **{key: form})
    try:
        services.save_variant(product, form, variant=variant, by=request.user)
    except services.CatalogError as exc:
        return _studio_response(request, product, "variants", str(exc), "error", **{key: form})
    audit.log(request.user, product, audit.CHANGE, f"ویرایش تنوع {variant.sku}")
    return _studio_response(request, product, "variants", "تنوع ذخیره شد")


@panel_view(VIEW, "catalog.change_variant")
@require_POST
def variant_action(request, pk, variant_pk, action):
    product = _load(pk)
    variant = get_object_or_404(product.variants.select_related("product"), pk=variant_pk)
    if action in ("up", "down"):
        with transaction.atomic():
            ordering.reorder(list(product.variants.order_by("sort", "pk")), variant.pk, action)
        return _studio_response(request, product, "variants")
    if action == "delete":
        if not _need(request, "catalog.delete_variant"):
            return _studio_response(request, product, "variants", "اجازه‌ی حذف تنوع را ندارید", "error")
        try:
            services.delete_variant(variant)
        except services.CatalogError as exc:
            return _studio_response(request, product, "variants", str(exc), "error")
        audit.log(request.user, product, audit.CHANGE, f"حذف تنوع {variant.sku}")
        return _studio_response(request, product, "variants", "تنوع حذف شد")
    return _studio_response(request, product, "variants", "عمل نامعتبر است", "error")


# --- specifications --------------------------------------------------------


@panel_view(VIEW, "catalog.change_productspecvalue")
@require_POST
def product_specs(request, pk):
    product = _load(pk)
    attributes = list(specs.applicable_attributes(product.category))
    values = {v.attribute_id: v for v in product.spec_values.all()}
    form = SpecsForm(request.POST, attributes=attributes, values=values)
    if not form.is_valid():
        return _studio_response(request, product, "specs", "مقدارها را بررسی کنید", "error", specs_form=form)
    changed = services.save_specs(product, values, form.desired())
    if changed:
        audit.log(request.user, product, audit.CHANGE, "ویرایش مشخصات فنی")
    return _studio_response(request, product, "specs", "مشخصات ذخیره شد" if changed else "تغییری ثبت نشد")


@panel_view(VIEW, "catalog.change_productspecvalue")
@require_POST
def product_spec_remove(request, pk, value_pk):
    product = _load(pk)
    get_object_or_404(ProductSpecValue, pk=value_pk, product=product).delete()
    return _studio_response(request, product, "specs", "مقدار حذف شد")
