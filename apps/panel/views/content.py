"""Static pages and footer links in the panel (docs/09 module 10)."""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.core.models import FooterLink, StaticPage
from apps.panel import audit, htmx
from apps.panel.forms_marketing import FooterLinkForm, StaticPageForm
from apps.panel.permissions import panel_view
from apps.panel.views import common

V_PAGE, V_LINK = "core.view_staticpage", "core.view_footerlink"
FORM = "panel/marketing/form.html"


@panel_view(any_of=(V_PAGE, V_LINK))
@require_GET
def content_index(request):
    if request.user.has_perm(V_PAGE):
        return redirect("panel:pages")
    if request.user.has_perm(V_LINK):
        return redirect("panel:links")
    raise Http404


# --- static pages ----------------------------------------------------------


def page_delete_block(page: StaticPage) -> str:
    path = reverse("core:static_page", args=[page.slug])
    if FooterLink.objects.filter(url=path).exists():
        return "یک لینک فوتر به این صفحه اشاره می‌کند؛ ابتدا لینک را حذف کنید یا صفحه را غیرفعال کنید"
    return ""


@panel_view(V_PAGE)
@require_GET
def page_list(request):
    context = {"pages": StaticPage.objects.order_by("title"), "can_add": request.user.has_perm("core.add_staticpage")}
    return render(request, "panel/content/pages.html", context)


@panel_view(V_PAGE, "core.add_staticpage")
@require_http_methods(["GET", "POST"])
def page_new(request):
    return common.form_view(
        request, StaticPageForm, None, template=FORM, heading="صفحه‌ی تازه", back="panel:pages", noun="صفحه"
    )


@panel_view(V_PAGE, "core.change_staticpage")
@require_http_methods(["GET", "POST"])
def page_edit(request, pk):
    page = get_object_or_404(StaticPage, pk=pk)
    extra = {}
    if request.user.has_perm("core.delete_staticpage"):
        block = page_delete_block(page)
        extra = (
            {"delete_hint": block}
            if block
            else common.delete_context(request, "core.delete_staticpage", "panel:page_delete", pk, "این صفحه حذف شود؟")
        )
    return common.form_view(
        request, StaticPageForm, page, template=FORM, heading="ویرایش صفحه", back="panel:pages", noun="صفحه",
        extra=extra,
    )  # fmt: skip


@panel_view(V_PAGE, "core.delete_staticpage")
@require_POST
def page_delete(request, pk):
    page = get_object_or_404(StaticPage, pk=pk)
    reason = page_delete_block(page)
    if reason:
        htmx.flash(request, reason, "error")
        return redirect("panel:page_edit", pk=pk)
    audit.log(request.user, page, audit.DELETION, "حذف صفحه")
    page.delete()
    htmx.flash(request, "صفحه حذف شد")
    return redirect("panel:pages")


# --- footer links ----------------------------------------------------------


def _links_context(user) -> dict:
    links = list(FooterLink.objects.order_by("group", "sort", "pk"))
    return {
        "groups": [(label, [link for link in links if link.group == code]) for code, label in FooterLink.GROUP_CHOICES],
        "can_add": user.has_perm("core.add_footerlink"),
        "can_change": user.has_perm("core.change_footerlink"),
    }


def _link_prepare(link, form, request) -> None:
    if link.pk is None:
        link.sort = common.next_sort(FooterLink.objects.filter(group=link.group))


@panel_view(V_LINK)
@require_GET
def link_list(request):
    return render(request, "panel/content/links.html", _links_context(request.user))


@panel_view(V_LINK, "core.add_footerlink")
@require_http_methods(["GET", "POST"])
def link_new(request):
    return common.form_view(
        request, FooterLinkForm, None, template=FORM, heading="لینک تازه", back="panel:links", noun="لینک",
        prepare=_link_prepare,
    )  # fmt: skip


@panel_view(V_LINK, "core.change_footerlink")
@require_http_methods(["GET", "POST"])
def link_edit(request, pk):
    link = get_object_or_404(FooterLink, pk=pk)
    extra = common.delete_context(
        request, "core.delete_footerlink", "panel:link_delete", pk, "این لینک از فوتر حذف شود؟"
    )
    return common.form_view(
        request, FooterLinkForm, link, template=FORM, heading="ویرایش لینک", back="panel:links", noun="لینک",
        extra=extra,
    )  # fmt: skip


link_delete = common.delete_view(
    FooterLink, view=V_LINK, perm="core.delete_footerlink", back="panel:links", noun="لینک"
)
link_action = common.action_view(
    FooterLink,
    view=V_LINK,
    perm="core.change_footerlink",
    siblings=lambda link: FooterLink.objects.filter(group=link.group),
    context=_links_context,
    template="panel/content/_links_list.html",
    back="panel:links",
    noun="لینک",
)
