"""Helpers shared by the marketing and content views of the panel."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.panel import audit, htmx, ordering
from apps.panel.permissions import panel_view


def parse_id(raw) -> int:
    raw = str(raw or "")
    return int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= 12 else 0


def next_sort(queryset) -> int:
    top = queryset.aggregate(top=Max("sort"))["top"]
    return 0 if top is None else top + 1


def window_state(obj, now) -> str:
    """live | scheduled | expired | inactive for anything with is_active, starts_at and ends_at."""
    if not obj.is_active:
        return "inactive"
    if obj.starts_at and obj.starts_at > now:
        return "scheduled"
    if obj.ends_at and obj.ends_at <= now:
        return "expired"
    return "live"


def delete_context(request, perm: str, url_name: str, pk: int, confirm: str, hint: str = "") -> dict:
    if not request.user.has_perm(perm):
        return {}
    return {"delete_url": reverse(url_name, args=[pk]), "delete_confirm": confirm, "delete_hint": hint}


def form_view(request, form_class, instance, *, template, heading, back, noun, prepare=None, after=None, extra=None):
    """One create/edit page: validate, save (files and many-to-many too), audit, flash, redirect."""
    creating = instance is None
    form = form_class(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if prepare:
            prepare(obj, form, request)
        with transaction.atomic():
            obj.save()
            form.save_m2m()
        audit.log(request.user, obj, audit.ADDITION if creating else audit.CHANGE, f"ذخیره‌ی {noun}")
        htmx.flash(request, f"{noun} ذخیره شد")
        return redirect(after(obj) if after else back)
    context = {"form": form, "obj": instance, "heading": heading, "back_url": reverse(back), **(extra or {})}
    return render(request, template, context)


def apply_action(request, obj, action: str, siblings, noun: str) -> str:
    """up / down / toggle for a list with `sort` and `is_active`. Returns the toast message."""
    if action in ("up", "down"):
        with transaction.atomic():
            ordering.reorder(list(siblings.order_by("sort", "pk")), obj.pk, action)
        return "ترتیب ذخیره شد"
    if action == "toggle":
        obj.is_active = not obj.is_active
        obj.save(update_fields=["is_active", "updated_at"])
        audit.log(request.user, obj, audit.CHANGE, f"{'فعال' if obj.is_active else 'غیرفعال'} شدن {noun}")
        return f"{noun} فعال شد" if obj.is_active else f"{noun} غیرفعال شد"
    raise Http404


def list_response(request, template, context, message, back, level="success"):
    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect(back)
    return htmx.toast(render(request, template, context), message, level)


def delete_view(model, *, view, perm, back, noun):
    @panel_view(view, perm)
    @require_POST
    def delete(request, pk):
        obj = get_object_or_404(model, pk=pk)
        audit.log(request.user, obj, audit.DELETION, f"حذف {noun}")
        obj.delete()
        htmx.flash(request, f"{noun} حذف شد")
        return redirect(back)

    return delete


def action_view(model, *, view, perm, siblings, context, template, back, noun):
    @panel_view(view, perm)
    @require_POST
    def act(request, pk, action):
        obj = get_object_or_404(model, pk=pk)
        message = apply_action(request, obj, action, siblings(obj), noun)
        return list_response(request, template, context(request.user), message, back)

    return act
