"""Marketing in the panel: home layout, banners, collections, trust items (docs/09 module 9).

Every write goes through save()/delete(), so the marketing signals move the epoch exactly like the admin does.
"""

from __future__ import annotations

from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.models import Product
from apps.core.jalali import to_fa_digits
from apps.core.text import normalize_fa
from apps.marketing import services as marketing_services
from apps.marketing.models import Banner, Collection, CollectionItem, HomeBlock, TrustItem
from apps.panel import audit, htmx, ordering
from apps.panel.forms_marketing import BannerForm, CollectionForm, HomeBlockForm, RulePreviewForm, TrustItemForm
from apps.panel.permissions import panel_view
from apps.panel.views import common

V_BLOCK, V_BANNER = "marketing.view_homeblock", "marketing.view_banner"
V_COLLECTION, V_TRUST = "marketing.view_collection", "marketing.view_trustitem"
FORM = "panel/marketing/form.html"
STATE_LABELS = {"live": "در حال نمایش", "scheduled": "زمان‌بندی‌شده", "expired": "منقضی", "inactive": "غیرفعال"}
STATE_DOTS = {
    "live": "status-success",
    "scheduled": "status-info",
    "expired": "status-neutral",
    "inactive": "status-neutral",
}


@panel_view(any_of=(V_BLOCK, V_BANNER, V_COLLECTION, V_TRUST))
@require_GET
def marketing_index(request):
    for perm, name in (
        (V_BLOCK, "panel:blocks"),
        (V_BANNER, "panel:banners"),
        (V_COLLECTION, "panel:collections"),
        (V_TRUST, "panel:trust"),
    ):
        if request.user.has_perm(perm):
            return redirect(name)
    raise Http404


# --- home layout -----------------------------------------------------------


def _blocks_context(user) -> dict:
    return {
        "blocks": list(HomeBlock.objects.select_related("category", "collection").order_by("sort", "pk")),
        "can_add": user.has_perm("marketing.add_homeblock"),
        "can_change": user.has_perm("marketing.change_homeblock"),
    }


def _block_prepare(block, form, request) -> None:
    if block.pk is None:
        block.sort = common.next_sort(HomeBlock.objects.all())


@panel_view(V_BLOCK)
@require_GET
def block_list(request):
    return render(request, "panel/marketing/blocks.html", _blocks_context(request.user))


@panel_view(V_BLOCK, "marketing.add_homeblock")
@require_http_methods(["GET", "POST"])
def block_new(request):
    return common.form_view(
        request, HomeBlockForm, None, template=FORM, heading="بلوک تازه", back="panel:blocks", noun="بلوک",
        prepare=_block_prepare,
    )  # fmt: skip


@panel_view(V_BLOCK, "marketing.change_homeblock")
@require_http_methods(["GET", "POST"])
def block_edit(request, pk):
    block = get_object_or_404(HomeBlock, pk=pk)
    extra = common.delete_context(
        request, "marketing.delete_homeblock", "panel:block_delete", pk, "این بلوک از صفحه‌ی اصلی حذف شود؟"
    )
    return common.form_view(
        request, HomeBlockForm, block, template=FORM, heading="ویرایش بلوک", back="panel:blocks", noun="بلوک",
        extra=extra,
    )  # fmt: skip


block_delete = common.delete_view(
    HomeBlock, view=V_BLOCK, perm="marketing.delete_homeblock", back="panel:blocks", noun="بلوک"
)
block_action = common.action_view(
    HomeBlock,
    view=V_BLOCK,
    perm="marketing.change_homeblock",
    siblings=lambda block: HomeBlock.objects.all(),
    context=_blocks_context,
    template="panel/marketing/_blocks_list.html",
    back="panel:blocks",
    noun="بلوک",
)


# --- banners ---------------------------------------------------------------


def _target_text(banner: Banner) -> str:
    kind = banner.target_type
    if kind == Banner.TARGET_NONE:
        return "بدون لینک"
    if kind == Banner.TARGET_URL:
        return banner.target_url
    obj = {
        Banner.TARGET_PRODUCT: banner.target_product,
        Banner.TARGET_CATEGORY: banner.target_category,
        Banner.TARGET_COLLECTION: banner.target_collection,
    }.get(kind)
    name = (getattr(obj, "title", None) or getattr(obj, "name", "")) if obj else "حذف‌شده"
    return f"{banner.get_target_type_display()}: {name}"


def _banners_context(user) -> dict:
    now = timezone.now()
    banners = Banner.objects.select_related("target_product", "target_category", "target_collection")
    rows = []
    for banner in banners.order_by("placement", "sort", "pk"):
        state = common.window_state(banner, now)
        rows.append(
            {
                "banner": banner,
                "state": state,
                "label": STATE_LABELS[state],
                "dot": STATE_DOTS[state],
                "dead": marketing_services.banner_target_dead(banner),
                "target": _target_text(banner),
            }
        )
    groups = [
        (label, [row for row in rows if row["banner"].placement == code]) for code, label in Banner.PLACEMENT_CHOICES
    ]
    return {
        "groups": groups,
        "can_add": user.has_perm("marketing.add_banner"),
        "can_change": user.has_perm("marketing.change_banner"),
    }


def _banner_prepare(banner, form, request) -> None:
    if banner.pk is None:
        banner.sort = common.next_sort(Banner.objects.filter(placement=banner.placement))
    if form.cleaned_data.get("image_mobile_clear") and not request.FILES.get("image_mobile"):
        banner.image_mobile = ""


@panel_view(V_BANNER)
@require_GET
def banner_list(request):
    return render(request, "panel/marketing/banners.html", _banners_context(request.user))


@panel_view(V_BANNER, "marketing.add_banner")
@require_http_methods(["GET", "POST"])
def banner_new(request):
    return common.form_view(
        request, BannerForm, None, template=FORM, heading="بنر تازه", back="panel:banners", noun="بنر",
        prepare=_banner_prepare,
    )  # fmt: skip


@panel_view(V_BANNER, "marketing.change_banner")
@require_http_methods(["GET", "POST"])
def banner_edit(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    extra = common.delete_context(request, "marketing.delete_banner", "panel:banner_delete", pk, "این بنر حذف شود؟")
    return common.form_view(
        request, BannerForm, banner, template=FORM, heading="ویرایش بنر", back="panel:banners", noun="بنر",
        prepare=_banner_prepare, extra=extra,
    )  # fmt: skip


banner_delete = common.delete_view(
    Banner, view=V_BANNER, perm="marketing.delete_banner", back="panel:banners", noun="بنر"
)
banner_action = common.action_view(
    Banner,
    view=V_BANNER,
    perm="marketing.change_banner",
    siblings=lambda banner: Banner.objects.filter(placement=banner.placement),
    context=_banners_context,
    template="panel/marketing/_banners_list.html",
    back="panel:banners",
    noun="بنر",
)


# --- collections -----------------------------------------------------------


def _collections_context(user) -> dict:
    now = timezone.now()
    rows = []
    for collection in Collection.objects.annotate(item_total=Count("items")):
        state = common.window_state(collection, now)
        manual = collection.mode == Collection.MODE_MANUAL
        count = collection.item_total if manual else marketing_services.collection_products(collection)[0].count()
        rows.append(
            {
                "collection": collection,
                "state": state,
                "label": STATE_LABELS[state],
                "dot": STATE_DOTS[state],
                "count": count,
            }
        )
    return {"rows": rows, "can_add": user.has_perm("marketing.add_collection")}


def _items_context(collection, user) -> dict:
    return {
        "collection": collection,
        "items": list(collection.items.select_related("product__main_image").order_by("sort", "pk")),
        "can_items": user.has_perm("marketing.change_collectionitem"),
    }


def _items_response(request, collection, message, level="success"):
    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:collection_edit", pk=collection.pk)
    response = render(request, "panel/marketing/_items.html", _items_context(collection, request.user))
    return htmx.toast(response, message, level)


def _collection_prepare(collection, form, request) -> None:
    if form.cleaned_data.get("cover_clear") and not request.FILES.get("cover"):
        collection.cover = ""


@panel_view(V_COLLECTION)
@require_GET
def collection_list(request):
    return render(request, "panel/marketing/collections.html", _collections_context(request.user))


@panel_view(V_COLLECTION, "marketing.add_collection")
@require_http_methods(["GET", "POST"])
def collection_new(request):
    return common.form_view(
        request, CollectionForm, None, template="panel/marketing/collection_form.html", heading="مجموعه‌ی تازه",
        back="panel:collections", noun="مجموعه", prepare=_collection_prepare,
        after=lambda saved: reverse("panel:collection_edit", args=[saved.pk]),
    )  # fmt: skip


@panel_view(V_COLLECTION, "marketing.change_collection")
@require_http_methods(["GET", "POST"])
def collection_edit(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    blocks = HomeBlock.objects.filter(collection=collection).count()
    banners = Banner.objects.filter(target_collection=collection).count()
    confirm = to_fa_digits(
        f"مجموعه حذف شود؟ {blocks} بلوک صفحه‌ی اصلی هم حذف می‌شود و {banners} بنر بدون مقصد می‌ماند و دیگر نمایش داده نمی‌شود"
    )
    extra = {
        **_items_context(collection, request.user),
        **common.delete_context(request, "marketing.delete_collection", "panel:collection_delete", pk, confirm),
        "public_url": collection.get_absolute_url() if collection.is_live() else "",
    }
    return common.form_view(
        request, CollectionForm, collection, template="panel/marketing/collection_form.html",
        heading="ویرایش مجموعه", back="panel:collections", noun="مجموعه", prepare=_collection_prepare, extra=extra,
        after=lambda saved: reverse("panel:collection_edit", args=[saved.pk]),
    )  # fmt: skip


collection_delete = common.delete_view(
    Collection, view=V_COLLECTION, perm="marketing.delete_collection", back="panel:collections", noun="مجموعه"
)


@panel_view(V_COLLECTION)
@require_GET
def collection_preview(request):
    """How many products a rule matches right now, before anything is saved."""
    form = RulePreviewForm(request.GET)
    if not form.is_valid():
        return HttpResponse("شروط را بررسی کنید")
    data = form.cleaned_data
    count = marketing_services.rule_queryset(
        only_in_stock=data["only_in_stock"],
        min_discount_pct=data["min_discount_pct"],
        min_price=data["min_price"],
        max_price=data["max_price"],
        brand_ids=[brand.pk for brand in data["brands"]],
        category_paths=[category.path for category in data["categories"]],
    ).count()
    return HttpResponse(to_fa_digits(f"با این شروط هم‌اکنون {count} محصول نمایش داده می‌شود"))


@panel_view(V_COLLECTION, "marketing.add_collectionitem")
@require_GET
def collection_item_search(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    text = normalize_fa(request.GET.get("q", ""), for_search=True)[:60]
    products = []
    if len(text) >= 2:
        taken = collection.items.values("product_id")
        found = Product.objects.published().filter(search_text__contains=text).exclude(pk__in=taken)
        products = list(found.select_related("main_image").order_by("-created_at")[:8])
    return render(request, "panel/marketing/_item_results.html", {"collection": collection, "products": products})


@panel_view(V_COLLECTION, "marketing.add_collectionitem")
@require_POST
def collection_item_add(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    product = Product.objects.filter(pk=common.parse_id(request.POST.get("product"))).first()
    if product is None:
        return _items_response(request, collection, "محصول پیدا نشد", "error")
    _, created = CollectionItem.objects.get_or_create(
        collection=collection, product=product, defaults={"sort": common.next_sort(collection.items.all())}
    )
    if created:
        audit.log(request.user, collection, audit.CHANGE, "افزودن محصول به مجموعه")
    return _items_response(request, collection, "به مجموعه اضافه شد")


@panel_view(V_COLLECTION, "marketing.change_collectionitem")
@require_POST
def collection_item_action(request, pk, item_pk, action):
    collection = get_object_or_404(Collection, pk=pk)
    item = get_object_or_404(collection.items, pk=item_pk)
    if action in ("up", "down"):
        ordering.reorder(list(collection.items.order_by("sort", "pk")), item.pk, action)
        return _items_response(request, collection, "ترتیب ذخیره شد")
    if action == "remove":
        if not request.user.has_perm("marketing.delete_collectionitem"):
            return _items_response(request, collection, "اجازه‌ی حذف ندارید", "error")
        item.delete()
        audit.log(request.user, collection, audit.CHANGE, "برداشتن محصول از مجموعه")
        return _items_response(request, collection, "از مجموعه برداشته شد")
    raise Http404


# --- trust items -----------------------------------------------------------


def _trust_context(user) -> dict:
    return {
        "items": list(TrustItem.objects.order_by("sort", "pk")),
        "can_add": user.has_perm("marketing.add_trustitem"),
        "can_change": user.has_perm("marketing.change_trustitem"),
    }


def _trust_prepare(item, form, request) -> None:
    if item.pk is None:
        item.sort = common.next_sort(TrustItem.objects.all())


@panel_view(V_TRUST)
@require_GET
def trust_list(request):
    return render(request, "panel/marketing/trust.html", _trust_context(request.user))


@panel_view(V_TRUST, "marketing.add_trustitem")
@require_http_methods(["GET", "POST"])
def trust_new(request):
    return common.form_view(
        request, TrustItemForm, None, template="panel/marketing/trust_form.html", heading="مزیت تازه",
        back="panel:trust", noun="مزیت", prepare=_trust_prepare,
    )  # fmt: skip


@panel_view(V_TRUST, "marketing.change_trustitem")
@require_http_methods(["GET", "POST"])
def trust_edit(request, pk):
    item = get_object_or_404(TrustItem, pk=pk)
    extra = common.delete_context(request, "marketing.delete_trustitem", "panel:trust_delete", pk, "این مزیت حذف شود؟")
    return common.form_view(
        request, TrustItemForm, item, template="panel/marketing/trust_form.html", heading="ویرایش مزیت",
        back="panel:trust", noun="مزیت", extra=extra,
    )  # fmt: skip


trust_delete = common.delete_view(
    TrustItem, view=V_TRUST, perm="marketing.delete_trustitem", back="panel:trust", noun="مزیت"
)
trust_action = common.action_view(
    TrustItem,
    view=V_TRUST,
    perm="marketing.change_trustitem",
    siblings=lambda item: TrustItem.objects.all(),
    context=_trust_context,
    template="panel/marketing/_trust_list.html",
    back="panel:trust",
    noun="مزیت",
)
