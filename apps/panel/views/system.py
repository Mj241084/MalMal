"""System section of the panel (docs/09 module 13): SMS log, staff, audit trail, launch readiness."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts import services
from apps.accounts.models import User
from apps.core.management.commands import check_launch
from apps.core.text import normalize_digits
from apps.notifications import sms
from apps.notifications.models import SmsLog
from apps.panel import audit, htmx, queries
from apps.panel.forms_settings import StaffCreateForm, StaffForm, StaffPasswordForm, first_error
from apps.panel.permissions import panel_view
from apps.panel.views import common

logger = logging.getLogger(__name__)
PAGE_SIZE = 25
ACTIONS = {audit.ADDITION: "افزودن", audit.CHANGE: "ویرایش", audit.DELETION: "حذف"}


@panel_view(superuser=True)
@require_GET
def system_index(request):
    return redirect("panel:staff")


# --- SMS log -----------------------------------------------------------------


def _sms_context(params) -> dict:
    queryset = SmsLog.objects.all()
    status = params.get("status") if params.get("status") in dict(SmsLog.STATUS_CHOICES) else ""
    kind = params.get("kind") if params.get("kind") in sms.TEMPLATE_SETTINGS else ""
    if status:
        queryset = queryset.filter(status=status)
    if kind:
        queryset = queryset.filter(kind=kind)
    digits = "".join(ch for ch in normalize_digits(params.get("q", "")) if ch.isdigit())
    if digits:
        queryset = queryset.filter(mobile__contains=digits)
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))
    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {
        key: value
        for key, value in (
            ("q", params.get("q", "")), ("status", status), ("kind", kind),
            ("from", params.get("from", "")), ("to", params.get("to", "")),
        )
        if value
    }  # fmt: skip
    return {
        "page_obj": page_obj, "q": params.get("q", ""), "status": status, "kind": kind,
        "date_from": params.get("from", ""), "date_to": params.get("to", ""),
        "status_choices": SmsLog.STATUS_CHOICES, "kinds": sorted(sms.TEMPLATE_SETTINGS), "qs": urlencode(filters),
    }  # fmt: skip


@panel_view("notifications.view_smslog")
@require_GET
def sms_list(request):
    context = _sms_context(request.GET)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/system/_sms_results.html", context)
    return render(request, "panel/system/sms.html", context)


# --- staff -------------------------------------------------------------------


@panel_view(superuser=True)
@require_GET
def staff_list(request):
    staff = User.objects.filter(is_staff=True).prefetch_related("groups").order_by("-is_active", "mobile")
    return render(request, "panel/system/staff.html", {"staff": staff, "groups_exist": Group.objects.exists()})


@panel_view(superuser=True)
@require_http_methods(["GET", "POST"])
def staff_new(request):
    form = StaffCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            member = services.create_staff_user(
                data["mobile"], data["password1"], [g.name for g in data["groups"]],
                first_name=data["first_name"], last_name=data["last_name"], allow_existing=False,
            )  # fmt: skip
        except services.StaffError as exc:
            form.add_error(None, str(exc))
        else:
            audit.log(request.user, member, audit.ADDITION, "ساخت همکار")
            htmx.flash(request, "همکار ساخته شد")
            return redirect("panel:staff_edit", pk=member.pk)
    return render(
        request,
        "panel/system/staff_form.html",
        {"form": form, "heading": "همکار تازه", "member": None, "label": "ساخت همکار"},
    )


def _member(pk) -> User:
    return get_object_or_404(User, pk=pk, is_staff=True)


@panel_view(superuser=True)
@require_http_methods(["GET", "POST"])
def staff_edit(request, pk):
    member = _member(pk)
    if member.is_superuser:
        htmx.flash(request, services.STAFF_ERRORS["superuser"], "error")
        return redirect("panel:staff")
    form = StaffForm(
        request.POST or None,
        initial={
            "first_name": member.first_name,
            "last_name": member.last_name,
            "groups": list(member.groups.values_list("pk", flat=True)),
        },
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.update_staff_profile(
                member,
                first_name=data["first_name"],
                last_name=data["last_name"],
                group_names=[g.name for g in data["groups"]],
            )
        except services.StaffError as exc:
            form.add_error(None, str(exc))
        else:
            audit.log(request.user, member, audit.CHANGE, "ویرایش همکار")
            htmx.flash(request, "ذخیره شد")
            return redirect("panel:staff_edit", pk=pk)
    context = {
        "form": form,
        "heading": "ویرایش همکار",
        "member": member,
        "label": "ذخیره",
        "password_form": StaffPasswordForm(),
    }
    return render(request, "panel/system/staff_form.html", context)


@panel_view(superuser=True)
@require_POST
def staff_password(request, pk):
    member = _member(pk)
    form = StaffPasswordForm(request.POST)
    if not form.is_valid():
        htmx.flash(request, first_error(form), "error")
        return redirect("panel:staff_edit", pk=pk)
    try:
        services.reset_staff_password(member, form.cleaned_data["password1"])
    except services.StaffError as exc:
        htmx.flash(request, str(exc), "error")
        return redirect("panel:staff_edit", pk=pk)
    audit.log(request.user, member, audit.CHANGE, "ریست رمز همکار")
    htmx.flash(request, "رمز تغییر کرد و همکار از همه‌ی دستگاه‌ها خارج شد")
    return redirect("panel:staff_edit", pk=pk)


@panel_view(superuser=True)
@require_POST
def staff_active(request, pk):
    member = _member(pk)
    active = request.POST.get("to") == "1"
    try:
        services.set_staff_active(member, by=request.user, active=active)
    except services.StaffError as exc:
        htmx.flash(request, str(exc), "error")
    else:
        audit.log(request.user, member, audit.CHANGE, "فعال‌سازی همکار" if active else "غیرفعال‌سازی همکار")
        htmx.flash(request, "همکار فعال شد" if active else "همکار غیرفعال شد")
    return redirect("panel:staff")


# --- audit trail -------------------------------------------------------------


def _audit_context(params) -> dict:
    base = LogEntry.objects.filter(change_message__startswith=audit.PREFIX)
    queryset = base.select_related("user", "content_type")
    user_id, type_id = common.parse_id(params.get("user")), common.parse_id(params.get("type"))
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if type_id:
        queryset = queryset.filter(content_type_id=type_id)
    queryset = queries.within(queryset, "action_time", *queries.day_range(params.get("from"), params.get("to")))
    page_obj = Paginator(queryset.order_by("-action_time", "-pk"), 30).get_page(params.get("page"))
    type_ids = base.order_by().values_list("content_type_id", flat=True).distinct()
    filters = {
        key: value
        for key, value in (("user", user_id or ""), ("type", type_id or ""), ("from", params.get("from", "")), ("to", params.get("to", "")))
        if value
    }  # fmt: skip
    return {
        "page_obj": page_obj,
        "rows": [
            {"entry": e, "action": ACTIONS.get(e.action_flag, ""), "message": e.change_message.removeprefix(audit.PREFIX)}
            for e in page_obj.object_list
        ],
        "users": list(User.objects.filter(is_staff=True).order_by("mobile")),
        "types": list(ContentType.objects.filter(pk__in=type_ids).order_by("app_label", "model")),
        "user_id": user_id, "type_id": type_id,
        "date_from": params.get("from", ""), "date_to": params.get("to", ""), "qs": urlencode(filters),
    }  # fmt: skip


@panel_view(superuser=True)
@require_GET
def audit_list(request):
    context = _audit_context(request.GET)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/system/_audit_results.html", context)
    return render(request, "panel/system/audit.html", context)


# --- launch readiness --------------------------------------------------------


@panel_view(superuser=True)
@require_GET
def launch(request):
    """Heavy (Redis, migrations, FTS): runs only on this page, and again with its «بررسی دوباره» button."""
    findings, failed = [], False
    try:
        for level, text, fix in check_launch.collect_detailed():
            findings.append({"error": level == check_launch.ERROR, "text": text, "fix": reverse(fix) if fix else ""})
    except Exception:
        logger.exception("check_launch failed")
        failed = True
    errors = sum(1 for item in findings if item["error"])
    context = {
        "findings": findings, "errors": errors, "warnings": len(findings) - errors, "failed": failed,
        "backup": queries.backup_status(),
    }  # fmt: skip
    template = "panel/system/_launch_results.html" if request.htmx else "panel/system/launch.html"
    return render(request, template, context)
