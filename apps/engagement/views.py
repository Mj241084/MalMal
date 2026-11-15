"""Likes, social text, reviews and the wishlist (docs/02 §9, §11, D12, D13)."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts import ratelimit
from apps.catalog.filters import PAGE_SIZE
from apps.catalog.models import Product
from apps.core.decorators import htmx_login_redirect, login_required_htmx
from apps.engagement import services, social
from apps.engagement.forms import ReviewForm
from apps.engagement.models import Like, Review

MAX_STATE_IDS = 60
REVIEWS_PER_PAGE = 10
REVIEWS_PER_HOUR = 5


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _private(response):
    response["Cache-Control"] = "private, no-store"
    return response


def _visible_product(request, pk: int) -> Product:
    product = get_object_or_404(Product, pk=pk)
    if not product.is_active and not request.user.is_staff:
        raise Http404
    return product


def _parse_ids(raw: str | None) -> list[int]:
    ids: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isascii() and part.isdigit() and int(part) not in ids:
            ids.append(int(part))
        if len(ids) == MAX_STATE_IDS:
            break
    return ids


# --- likes -----------------------------------------------------------------


@require_GET
def like_state_view(request):
    """Hearts of the given products that the viewer liked, as OOB buttons. One query for any number of cards."""
    if not request.user.is_authenticated:
        return HttpResponse(status=204)
    ids = _parse_ids(request.GET.get("ids"))
    liked = (
        list(Like.objects.filter(user=request.user, product_id__in=ids).values_list("product_id", flat=True))
        if ids
        else []
    )
    if not liked:
        return HttpResponse(status=204)
    return _private(render(request, "partials/_like_oob.html", {"liked_ids": liked}))


@login_required_htmx
@require_POST
def like_set_view(request, pk):
    product = _visible_product(request, pk)
    liked = services.set_like(request.user, product.pk, request.POST.get("state") != "0")
    context = {"liked_ids": [product.pk] if liked else [], "unliked_ids": [] if liked else [product.pk]}
    if request.POST.get("ctx") == "page":  # the product page also refreshes its social text
        product.refresh_from_db(fields=["like_count", "purchase_count_30d"])
        context.update(
            with_social=True,
            product=product,
            lines=social.product_lines(product, liked=liked),
            rating=social.rating_summary(product),
        )
    return _private(render(request, "partials/_like_oob.html", context))


@login_required_htmx
@require_GET
def wishlist_view(request):
    likes = (
        Like.objects.filter(user=request.user, product__status=Product.STATUS_ACTIVE)
        .select_related("product__brand", "product__category", "product__main_image")
        .order_by("-created_at", "-id")
    )
    page_obj = Paginator(likes, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {"page_obj": page_obj, "products": [like.product for like in page_obj.object_list]}
    template = "partials/_wishlist_results.html" if request.htmx else "pages/wishlist.html"
    return _private(render(request, template, context))


# --- social text -----------------------------------------------------------


@require_GET
def product_social_view(request, pk):
    product = _visible_product(request, pk)
    liked = request.user.is_authenticated and Like.objects.filter(user=request.user, product=product).exists()
    context = {
        "product": product,
        "lines": social.product_lines(product, liked=liked),
        "rating": social.rating_summary(product),
    }
    return _private(render(request, "partials/_social_product.html", context))


# --- reviews ---------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def reviews_view(request, pk):
    """Reviews block of the product page: summary, the viewer's own review/form, approved reviews."""
    product = _visible_product(request, pk)
    signed_in = request.user.is_authenticated
    own = Review.objects.filter(user=request.user, product=product).first() if signed_in else None
    form, notice = None, ""

    if request.method == "POST":
        if not signed_in:
            return htmx_login_redirect(request)
        form = ReviewForm(request.POST)
        if form.is_valid():
            if ratelimit.consume(f"review:u:{request.user.pk}", REVIEWS_PER_HOUR, ratelimit.HOUR):
                own = services.submit_review(request.user, product, **form.cleaned_data)
                product.refresh_from_db(fields=["review_count", "rating_sum", "rating_avg"])
                form, notice = None, "نظر شما ثبت شد و بعد از تایید نمایش داده می‌شود"
            else:
                form.add_error(None, "تعداد ثبت نظر زیاد شد. کمی بعد دوباره تلاش کنید")
    elif signed_in and (own is None or request.GET.get("edit")):
        form = ReviewForm(initial={"rating": own.rating, "body": own.body} if own else None)

    page = _int(request.GET.get("page")) or 1
    public = Review.objects.filter(product=product, status=Review.APPROVED).select_related("user")
    if own is not None:
        public = public.exclude(pk=own.pk)  # the author sees their own review in its own card
    page_obj = Paginator(public.order_by("-created_at", "-id"), REVIEWS_PER_PAGE).get_page(page)

    context = {
        "product": product,
        "own": own,
        "form": form,
        "notice": notice,
        "page_obj": page_obj,
        "rating": social.rating_summary(product),
    }
    items_only = request.method == "GET" and page > 1
    return _private(
        render(request, "partials/_review_items.html" if items_only else "partials/_reviews_block.html", context)
    )
