"""Reviews in the panel: the moderation inbox (docs/09 module 8). Every decision goes through engagement.services.moderate."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.jalali import to_fa_digits
from apps.core.text import normalize_fa
from apps.engagement import services
from apps.engagement.models import Review
from apps.panel import audit, badges, htmx, queries
from apps.panel.forms_catalog import multiline
from apps.panel.permissions import panel_view

PAGE_SIZE = 20
MAX_BATCH = 50
VIEW, CHANGE = "engagement.view_review", "engagement.change_review"
TABS = (
    ("pending", "در انتظار تایید", Review.PENDING),
    ("approved", "تاییدشده", Review.APPROVED),
    ("rejected", "تایید نشد", Review.REJECTED),
    ("all", "همه", None),
)
TAB_STATUS = {code: status for code, _label, status in TABS}


def _tab_counts() -> dict[str, int]:
    by_status = dict(Review.objects.order_by().values_list("status").annotate(n=Count("pk")))  # one query
    return {
        code: sum(by_status.values()) if status is None else by_status.get(status, 0) for code, _label, status in TABS
    }


def _list_context(params, user) -> dict:
    tab = params.get("tab") if params.get("tab") in TAB_STATUS else "pending"
    queryset = Review.objects.select_related("product__main_image", "user")
    if TAB_STATUS[tab]:
        queryset = queryset.filter(status=TAB_STATUS[tab])
    queryset = queryset.order_by("created_at", "pk") if tab == "pending" else queryset.order_by("-created_at", "-pk")
    page_obj = Paginator(queryset, PAGE_SIZE).get_page(params.get("page"))
    counts = _tab_counts()
    return {
        "tab": tab,
        "tabs": [(code, label, counts[code]) for code, label, _status in TABS],
        "page_obj": page_obj,
        "qs": urlencode({"tab": tab}),
        "hidden": [("tab", tab), ("page", page_obj.number)],
        "can_moderate": user.has_perm(CHANGE),
    }


def _entries(raw: list[str]) -> list[tuple[int, int]]:
    """«pk:stamp» pairs posted by the cards; junk is dropped."""
    entries = []
    for value in raw[:MAX_BATCH]:
        pk, _, seen = value.partition(":")
        if pk.isascii() and pk.isdigit() and len(pk) <= 12 and seen.isascii() and seen.isdigit() and len(seen) <= 20:
            entries.append((int(pk), int(seen)))
    return entries


def _respond(request, message: str, level: str):
    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:reviews")
    if request.POST.get("ctx") == "dashboard":
        response = render(request, "panel/partials/_review_queue.html", queries.review_queue(request.user))
    else:
        response = render(request, "panel/reviews/_list_results.html", _list_context(request.POST, request.user))
    return htmx.toast(response, message, level)


@panel_view(VIEW)
@require_GET
def review_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/reviews/_list_results.html", context)
    return render(request, "panel/reviews/list.html", context)


@panel_view(VIEW, CHANGE)
@require_POST
def review_decide(request):
    """Approve or reject one or many reviews. Each entry carries the version the moderator saw."""
    status = {"approve": Review.APPROVED, "reject": Review.REJECTED}.get(request.POST.get("action"))
    entries = _entries(request.POST.getlist("review"))
    if status is None or not entries:
        return _respond(request, "نظری انتخاب نشده است", "error")

    reason = normalize_fa(request.POST.get("reason", ""))[:200]
    done = 0
    for pk, seen in entries:
        with transaction.atomic():
            review = Review.objects.filter(pk=pk).first()
            if review is None or review.status == status or queries.stamp(review.updated_at) != seen:
                continue  # edited by the customer or decided by a colleague meanwhile
            services.moderate(review, status, by=request.user, reason=reason)
        audit.log(request.user, review, audit.CHANGE, "تایید نظر" if status == Review.APPROVED else "رد نظر")
        done += 1
    badges.bust("reviews_pending")

    skipped = len(entries) - done
    verb = "تایید شد" if status == Review.APPROVED else "رد شد"
    message = to_fa_digits(f"{done} نظر {verb}" + (f"، {skipped} مورد هم‌زمان تغییر کرده بود" if skipped else ""))
    return _respond(request, message, "success" if done and not skipped else "warning")


@panel_view(VIEW, CHANGE)
@require_POST
def review_reply(request, pk):
    review = get_object_or_404(Review, pk=pk)
    reply = multiline(request.POST.get("reply", ""))[:1000]
    if reply != review.admin_reply:
        review.admin_reply = reply
        review.save(update_fields=["admin_reply", "updated_at"])
        audit.log(request.user, review, audit.CHANGE, "پاسخ فروشگاه" if reply else "حذف پاسخ فروشگاه")
    return _respond(request, "پاسخ ذخیره شد" if reply else "پاسخ حذف شد", "success")
