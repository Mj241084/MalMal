"""Categories and their specification attributes in the panel (docs/09 module 5)."""

from __future__ import annotations

from collections import defaultdict

from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog import services
from apps.catalog.models import Category
from apps.panel import audit, htmx, ordering
from apps.panel.forms_catalog import CategoryForm, SpecAttributeForm
from apps.panel.permissions import panel_view

VIEW = "catalog.view_category"


def _flatten(categories) -> list:
    """Depth-first tree order; siblings by (menu_order, name). Marks the first and last child for the arrows."""
    by_parent = defaultdict(list)
    for category in categories:
        by_parent[category.parent_id].append(category)
    for rows in by_parent.values():
        rows.sort(key=lambda c: (c.menu_order, c.name, c.pk))
    flat = []

    def walk(parent_id):
        siblings = by_parent.get(parent_id, [])
        for index, category in enumerate(siblings):
            category.is_first, category.is_last = index == 0, index == len(siblings) - 1
            flat.append(category)
            walk(category.pk)

    walk(None)
    return flat


def _tree_context(user) -> dict:
    rows = Category.objects.annotate(product_count=Count("products")).select_related("parent")
    return {"categories": _flatten(list(rows)), "can_change": user.has_perm("catalog.change_category")}


@panel_view(VIEW)
@require_GET
def category_list(request):
    context = _tree_context(request.user)
    context["can_add"] = request.user.has_perm("catalog.add_category")
    return render(request, "panel/categories/list.html", context)


@panel_view(VIEW, "catalog.change_category")
@require_POST
def category_move(request, pk, direction):
    category = get_object_or_404(Category, pk=pk)
    if direction not in ("up", "down"):
        raise Http404
    with transaction.atomic():
        siblings = sorted(
            Category.objects.filter(parent_id=category.parent_id), key=lambda c: (c.menu_order, c.name, c.pk)
        )
        ordering.reorder(siblings, category.pk, direction, "menu_order")
    return render(request, "panel/categories/_tree.html", _tree_context(request.user))


def _save_category(request, form):
    category = form.save(commit=False)
    if form.cleaned_data["logo_clear"] and not request.FILES.get("logo"):
        category.logo = ""
    category.save()
    return category


def _form_page(request, category):
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        saved = _save_category(request, form)
        audit.log(request.user, saved, audit.CHANGE if category else audit.ADDITION, "ذخیره‌ی دسته")
        htmx.flash(request, "دسته ذخیره شد")
        return redirect("panel:category_edit", pk=saved.pk)
    context = {
        "form": form,
        "category": category,
        "delete_block": services.category_delete_block(category) if category else "",
        "can_delete": request.user.has_perm("catalog.delete_category"),
        **(_attrs_context(category, request.user) if category else {}),
    }
    return render(request, "panel/categories/form.html", context)


@panel_view(VIEW, "catalog.add_category")
@require_http_methods(["GET", "POST"])
def category_new(request):
    return _form_page(request, None)


@panel_view(VIEW, "catalog.change_category")
@require_http_methods(["GET", "POST"])
def category_edit(request, pk):
    return _form_page(request, get_object_or_404(Category, pk=pk))


@panel_view(VIEW, "catalog.delete_category")
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        audit.log(request.user, category, audit.DELETION, "حذف دسته")
        services.delete_category(category)
    except services.CatalogError as exc:
        htmx.flash(request, str(exc), "error")
        return redirect("panel:category_edit", pk=pk)
    htmx.flash(request, "دسته حذف شد")
    return redirect("panel:categories")


# --- specification attributes ---------------------------------------------


def _attrs_context(category, user, forms=None) -> dict:
    forms = forms or {}
    attributes = list(category.spec_attributes.annotate(value_count=Count("values")).order_by("sort", "pk"))
    rows = [(a, forms.get(a.pk) or SpecAttributeForm(instance=a, auto_id=f"attr{a.pk}_%s")) for a in attributes]
    new_form = forms.get("new") or SpecAttributeForm(initial={"sort": len(attributes)}, auto_id="attrnew_%s")
    return {
        "rows": rows,
        "new_form": new_form,
        "attrs_category": category,
        "can_attr": user.has_perm("catalog.change_specattribute"),
    }


def _attrs_response(request, category, message, level="success", forms=None):
    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:category_edit", pk=category.pk)
    context = _attrs_context(category, request.user, forms)
    response = HttpResponse(render_to_string("panel/categories/_sec_attrs.html", context, request))
    return htmx.toast(response, message, level)


@panel_view(VIEW, "catalog.add_specattribute")
@require_POST
def spec_new(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = SpecAttributeForm(request.POST, auto_id="attrnew_%s")
    if not form.is_valid():
        return _attrs_response(request, category, "اطلاعات مشخصه را بررسی کنید", "error", {"new": form})
    services.save_spec_attribute(form, category)
    audit.log(request.user, category, audit.CHANGE, f"افزودن مشخصه {form.instance.name}")
    return _attrs_response(request, category, "مشخصه ذخیره شد")


@panel_view(VIEW, "catalog.change_specattribute")
@require_POST
def spec_edit(request, pk, spec_pk):
    category = get_object_or_404(Category, pk=pk)
    attribute = get_object_or_404(category.spec_attributes, pk=spec_pk)
    form = SpecAttributeForm(request.POST, instance=attribute, auto_id=f"attr{attribute.pk}_%s")
    if not form.is_valid():
        return _attrs_response(request, category, "اطلاعات مشخصه را بررسی کنید", "error", {attribute.pk: form})
    services.save_spec_attribute(form, category)
    audit.log(request.user, category, audit.CHANGE, f"ویرایش مشخصه {attribute.name}")
    return _attrs_response(request, category, "مشخصه ذخیره شد")


@panel_view(VIEW, "catalog.change_specattribute")
@require_POST
def spec_action(request, pk, spec_pk, action):
    category = get_object_or_404(Category, pk=pk)
    attribute = get_object_or_404(category.spec_attributes, pk=spec_pk)
    if action in ("up", "down"):
        with transaction.atomic():
            ordering.reorder(list(category.spec_attributes.order_by("sort", "pk")), attribute.pk, action)
        return _attrs_response(request, category, "ترتیب ذخیره شد")
    if action == "delete":
        if not request.user.has_perm("catalog.delete_specattribute"):
            return _attrs_response(request, category, "اجازه‌ی حذف مشخصه را ندارید", "error")
        audit.log(request.user, category, audit.CHANGE, f"حذف مشخصه {attribute.name}")
        services.delete_spec_attribute(attribute)
        return _attrs_response(request, category, "مشخصه حذف شد")
    raise Http404
