# بریف فاز ۱۲ — انبار و نظرها

> **قواعد اجرا (بر `CLAUDE.md` مقدم است):**
> - هر چیزی که لازم داری در همین بریف است. `docs/` و `skills/` را نخوان، TaskCreate نساز و گزارش ماجرا ننویس.
> - فقط فایل‌هایی را بخوان که می‌خواهی ویرایش کنی.
> - کامند اضافه، فایل اضافه، مرورگر، Playwright و اسکرین‌شات اجرا نکن. بررسی چشمی با من است.
> - فقط این کامندها مجازند: `makemigrations catalog -n variant_adjust_stock_permission`، `pnpm run build:css`، `uv run python scripts/build_sprite.py`، `uv run pytest apps/panel apps/catalog apps/engagement apps/core -q`، `uv run ruff check . --fix` و `uv run ruff format .`.
> - `migrate`، `setup_groups`، `runserver` و کل `pytest` را اجرا نکن.
> - کد انگلیسی، متن رابط فارسی با ارقام فارسی، فقط کلاس‌های منطقی RTL.

**تصمیم‌های قطعی این فاز (`[ASSUMPTION]`، سوال نپرس):**
- گروه‌های «فروش» و «محتوا» هر دو `catalog.adjust_stock` دارند.
- تنوع‌های «تخته‌ی انبار» فقط تنوع‌های فعالِ محصولاتِ فعال‌اند. با `?product=<pk>` همه‌ی تنوع‌های همان محصول دیده می‌شوند.
- `stock` در inline ادمین همیشه فقط‌خواندنی است.
- هر تصمیم روی نظر، نسخه‌ی دیده‌شده را چک می‌کند. اگر مشتری یا همکار دیگری آن نظر را میان دیدن و تصمیم تغییر داده باشد، تصمیم رد می‌شود.

---

## ۱. مجوز `adjust_stock`

در `apps/catalog/models.py`، کلاس `Variant.Meta` را اضافه کن:

```python
        permissions = [("adjust_stock", "Can change stock manually")]
```

سپس `uv run python manage.py makemigrations catalog -n variant_adjust_stock_permission` را اجرا کن.

## ۲. `apps/catalog/stock.py`

بعد از `InsufficientStock` اضافه کن:

```python
class StockConflict(Exception):
    """A manual change was refused: stock would go below zero, or it is no longer what the staff member saw."""

    def __init__(self, variant_id: int, current: int | None):
        super().__init__(f"Stock of variant {variant_id} is {current}")
        self.variant_id = variant_id
        self.current = current
```

و در انتهای فایل:

```python
def adjust_manual(variant_id: int, delta: int, *, note: str, expected_stock: int | None = None) -> int:
    """Staff stock change (D43): atomic compare-and-set, ledger row, aggregates, cache. Returns the new stock.

    Callers are inside transaction.atomic(). This path never goes through Variant.save(), so it does the
    aggregates, the cache bump and the «back in stock» marking itself.
    """
    if not delta:
        raise ValueError("delta must not be zero")
    rows = Variant.objects.filter(pk=variant_id, stock__gte=-delta)
    if expected_stock is not None:
        rows = rows.filter(stock=expected_stock)
    if not rows.update(stock=F("stock") + delta):
        current = Variant.objects.filter(pk=variant_id).values_list("stock", flat=True).first()
        raise StockConflict(variant_id, current)
    new_stock, active, product_id = (
        Variant.objects.filter(pk=variant_id).values_list("stock", "is_active", "product_id").get()
    )
    StockMovement.objects.create(
        variant_id=variant_id, delta=delta, reason=StockMovement.REASON_MANUAL, note=note[:255]
    )
    _invalidate_if_visible(variant_id, delta)
    refresh_products([product_id])
    if new_stock - delta == 0 and new_stock > 0 and active:  # a real restock: stock leaves zero
        from apps.engagement import back_in_stock

        transaction.on_commit(lambda: back_in_stock.mark_due(variant_id), robust=True)
    return new_stock
```

در `apps/catalog/services.py`، بخش «variants» (بعد از `delete_variant`) اضافه کن:

```python
def adjust_stock(variant_id: int, delta: int, *, reason: str, by, expected_stock: int | None = None) -> int:
    """Staff stock change (D43). Raises stock.StockConflict. Returns the new stock."""
    with transaction.atomic():
        return stock.adjust_manual(variant_id, delta, note=_note(reason, by), expected_stock=expected_stock)
```

## ۳. ادمین

در `apps/catalog/admin.py`، کلاس `VariantInline` را با این خط تکمیل کن (موجودی فقط از پنل عوض می‌شود):

```python
    readonly_fields = ("stock",)
```

## ۴. `setup_groups`

در `apps/accounts/management/commands/setup_groups.py`:
- به لیست `"محتوا"` اضافه کن: `("engagement", ("stocksubscription",), VIEW),`
- به لیست `"فروش"` همین ردیف را اضافه کن.
- `EXTRA` را این‌طور کن:

```python
EXTRA = {
    "محتوا": [("catalog", "adjust_stock")],
    "فروش": [("orders", "manage_order_status"), ("catalog", "adjust_stock")],
}
```

## ۵. زیرساخت پنل

### `apps/panel/queries.py`

importهای زیر را اضافه کن: `Count` از `django.db.models`، `Product` و `Variant` از `apps.catalog.models`، `to_fa_digits` از `apps.core.jalali`، `SiteSettings` از `apps.core.models`، `Review` از `apps.engagement.models`، و `sms` از `apps.notifications`. سپس این توابع را اضافه کن:

```python
def stamp(moment) -> int:
    """Version of a row as the moderator saw it: a decision is refused when the row changed meanwhile."""
    return int(moment.timestamp() * 1_000_000)


def reviews_pending() -> int:
    return Review.objects.filter(status=Review.PENDING).count()


def review_queue(user) -> dict:
    rows = list(Review.objects.filter(status=Review.PENDING).select_related("product").order_by("created_at", "pk")[:5])
    return {"review_queue": rows, "can_moderate": user.has_perm("engagement.change_review")}


def stock_board(product_id: int | None = None):
    """Variants the inventory page manages: sellable ones of live products, or every variant of one product."""
    if product_id:
        return Variant.objects.filter(product_id=product_id)
    return Variant.objects.filter(product__status=Product.STATUS_ACTIVE, is_active=True)


def stock_alert_count() -> int:
    return stock_board().filter(stock__lte=SiteSettings.get_solo().low_stock_threshold).count()


def wanted_out_of_stock(limit: int = 5) -> list[Variant]:
    return list(
        stock_board()
        .filter(stock__lte=0)
        .annotate(waiting=Count("stock_subscriptions", filter=Q(stock_subscriptions__notified_at__isnull=True)))
        .filter(waiting__gt=0)
        .select_related("product")
        .order_by("-waiting", "pk")[:limit]
    )


def restock_send_hint(now=None) -> str:
    """When the «back in stock» SMS of a queued restock goes out (docs/02 §13)."""
    if not sms.template_is_configured("back_in_stock"):
        return "قالب پیامک «موجود شد» تنظیم نشده است"
    site = SiteSettings.get_solo()
    if site.back_in_stock_start_hour <= timezone.localtime(now).hour < site.back_in_stock_end_hour:
        return "در اجرای بعدی (حداکثر ۱۰ دقیقه)"
    return f"از ساعت {to_fa_digits(f'{site.back_in_stock_start_hour:02d}:00')}"
```

### `apps/panel/badges.py`

`safe_cache_delete` را به import اضافه کن و این تابع را بنویس:

```python
def bust(key: str) -> None:
    """Drop a cached counter so the next render shows the real number."""
    safe_cache_delete(f"panel:badge:{key}")
```

### `apps/panel/providers.py`

```python
@badges.register("reviews_pending")
def reviews_pending() -> int:
    return queries.reviews_pending()
```

### `apps/panel/nav.py`

در `ITEMS` اضافه کن. نظرها بعد از `payments` و انبار بعد از `products`:

```python
(
    NavItem(
        "reviews",
        "نظرها",
        "panel:reviews",
        icon="message-square",
        group="daily",
        perms=("engagement.view_review",),
        badge="reviews_pending",
    ),
)
(NavItem("inventory", "انبار", "panel:inventory", icon="warehouse", group="catalog", perms=("catalog.view_variant",)),)
```

اگر `build_sprite.py` گفت یکی از این آیکون‌ها در منبع نیست، به‌ترتیب از `message-circle` و `boxes` استفاده کن.

### `apps/panel/templatetags/panel_tags.py`

import: `from apps.core.jalali import to_fa_digits` و `queries` به `from apps.panel import badges, nav`. سپس:

```python
REVIEW_DOT = {"pending": "status-warning", "approved": "status-success", "rejected": "status-error"}


@register.filter
def review_dot(status: str) -> str:
    return REVIEW_DOT.get(status, "status-neutral")


@register.filter
def stamp(moment) -> int:
    return queries.stamp(moment)


@register.filter
def signed(value) -> str:
    number = int(value)
    return to_fa_digits(f"+{number}" if number > 0 else str(number))
```

### `apps/panel/urls.py`

`inventory` و `reviews` را به import اضافه کن و این‌ها را قبل از بخش `# brands` بگذار:

```python
# inventory
(path("inventory/", inventory.inventory_list, name="inventory"),)
(path("inventory/ledger/", inventory.inventory_ledger, name="inventory_ledger"),)
(path("inventory/variants/<int:variant_pk>/adjust/", inventory.stock_adjust, name="stock_adjust"),)
# reviews
(path("reviews/", reviews.review_list, name="reviews"),)
(path("reviews/decide/", reviews.review_decide, name="review_decide"),)
(path("reviews/<int:pk>/reply/", reviews.review_reply, name="review_reply"),)
```

### `static/js/mm/panel.js`

انتخاب همه باید چک‌باکس‌هایی را هم بگیرد که با `form="..."` به فرم وصل‌اند. بلوک `data-check-all` را این‌طور عوض کن:

```js
    var all = target.closest("[data-check-all]");
    if (all && all.form) {
      /* form.elements also holds checkboxes tied with form="..." that sit outside the <form> element */
      Array.prototype.forEach.call(all.form.elements, function (box) {
        if (box.type === "checkbox" && !box.hasAttribute("data-check-all") && !box.disabled) box.checked = all.checked;
      });
      return;
    }
```

## ۶. انبار

### `apps/panel/forms_stock.py` (جدید)

```python
"""Manual stock change form of the panel (docs/09 module 7)."""

from __future__ import annotations

from django import forms

from apps.core.forms import FieldErrorAttrsMixin
from apps.core.widgets import FaDigitsInput, FaTextInput
from apps.panel.fields import FaIntegerField

MODES = (("add", "افزودن"), ("remove", "کم کردن"), ("set", "تنظیم به عدد (شمارش انبار)"))
MAX_STOCK = 100_000


class StockAdjustForm(FieldErrorAttrsMixin, forms.Form):
    mode = forms.ChoiceField(choices=MODES, initial="add", widget=forms.RadioSelect)
    amount = FaIntegerField(
        label="تعداد",
        min_value=0,
        max_value=MAX_STOCK,
        widget=FaDigitsInput(attrs={"class": "input w-full text-end num"}),
    )
    reason = forms.CharField(
        label="دلیل",
        max_length=150,
        widget=FaTextInput(attrs={"class": "input w-full", "autocomplete": "off"}),
        error_messages={"required": "دلیل تغییر را بنویسید"},
    )
    expected = forms.IntegerField(required=False, min_value=0, widget=forms.HiddenInput)

    def __init__(self, *args, variant, **kwargs):
        super().__init__(*args, **kwargs)
        self.variant = variant

    def clean(self):
        cleaned = super().clean()
        mode, amount, expected = cleaned.get("mode"), cleaned.get("amount"), cleaned.get("expected")
        if mode is None or amount is None:
            return cleaned
        if mode == "set":
            if expected is None:
                self.add_error(None, "موجودی فعلی نامشخص است؛ فرم را دوباره باز کنید")
                return cleaned
            cleaned["delta"] = amount - expected
        else:
            cleaned["delta"] = amount if mode == "add" else -amount
        if cleaned["delta"] == 0:
            self.add_error("amount", "این مقدار موجودی را تغییر نمی‌دهد")
        return cleaned
```

### `apps/panel/views/inventory.py` (جدید)

```python
"""Inventory in the panel: the stock board, the ledger and the one place staff change stock (docs/09 module 7)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from django_htmx.http import reswap, retarget

from apps.catalog import services
from apps.catalog.models import Product, StockMovement, Variant
from apps.catalog.stock import StockConflict
from apps.core.jalali import to_fa_digits
from apps.core.models import SiteSettings
from apps.core.text import normalize_fa
from apps.orders.models import OrderItem
from apps.panel import audit, htmx, queries
from apps.panel.forms_stock import StockAdjustForm
from apps.panel.permissions import panel_view

PAGE_SIZE = 25
VIEW, LEDGER, ADJUST = "catalog.view_variant", "catalog.view_stockmovement", "catalog.adjust_stock"
STATES = (("alert", "ناموجود و کم‌موجود"), ("out", "ناموجود"), ("low", "کم‌موجود"), ("in", "موجود"))
LIST_PARAMS = ("page", "q", "state", "product")


def _digits(raw) -> int | None:
    raw = str(raw or "")
    return int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= 12 else None


def _stock_context(params, user) -> dict:
    low = SiteSettings.get_solo().low_stock_threshold
    product_id = _digits(params.get("product"))
    queryset = (
        queries.stock_board(product_id)
        .select_related("product__main_image")
        .annotate(
            waiting=Count("stock_subscriptions", filter=Q(stock_subscriptions__notified_at__isnull=True)),
            queued=Count(
                "stock_subscriptions",
                filter=Q(
                    stock_subscriptions__restocked_at__isnull=False, stock_subscriptions__notified_at__isnull=True
                ),
            ),
        )
    )
    text = normalize_fa(params.get("q", ""), for_search=True)[:60]
    if text:
        queryset = queryset.filter(Q(sku__icontains=text) | Q(product__search_text__contains=text))
    state = params.get("state", "")
    if state == "alert":
        queryset = queryset.filter(stock__lte=low)
    elif state == "out":
        queryset = queryset.filter(stock__lte=0)
    elif state == "low":
        queryset = queryset.filter(stock__gt=0, stock__lte=low)
    elif state == "in":
        queryset = queryset.filter(stock__gt=low)
    else:
        state = ""

    page_obj = Paginator(queryset.order_by("stock", "product__title", "pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {
        key: value
        for key, value in (("q", params.get("q", "")), ("state", state), ("product", product_id or ""))
        if value
    }
    return {
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "state": state,
        "states": STATES,
        "filters": filters,
        "qs": urlencode(filters),
        "low": low,
        "product_note": (
            Product.objects.filter(pk=product_id).values_list("title", flat=True).first() if product_id else ""
        ),
        "send_hint": queries.restock_send_hint(),
        "can_stock": True,
        "can_ledger": user.has_perm(LEDGER),
        "can_adjust": user.has_perm(ADJUST),
        "can_open_product": user.has_perm("catalog.change_product"),
    }


@panel_view(VIEW)
@require_GET
def inventory_list(request):
    context = _stock_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/inventory/_stock_results.html", context)
    return render(request, "panel/inventory/list.html", context)


def _ledger_context(params, user) -> dict:
    queryset = StockMovement.objects.select_related("variant__product")
    text = normalize_fa(params.get("q", ""), for_search=True)[:60]
    if text:
        queryset = queryset.filter(Q(variant__sku__icontains=text) | Q(variant__product__search_text__contains=text))
    reason = params.get("reason") if params.get("reason") in dict(StockMovement.REASON_CHOICES) else ""
    if reason:
        queryset = queryset.filter(reason=reason)
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))

    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    item_ids = [m.order_item_id for m in page_obj.object_list if m.order_item_id]
    numbers = dict(OrderItem.objects.filter(pk__in=item_ids).values_list("pk", "order__number")) if item_ids else {}
    filters = {
        key: value
        for key, value in (
            ("q", params.get("q", "")),
            ("reason", reason),
            ("from", params.get("from", "")),
            ("to", params.get("to", "")),
        )
        if value
    }
    return {
        "page_obj": page_obj,
        "rows": [(m, numbers.get(m.order_item_id)) for m in page_obj.object_list],
        "q": params.get("q", ""),
        "reason": reason,
        "reasons": StockMovement.REASON_CHOICES,
        "date_from": params.get("from", ""),
        "date_to": params.get("to", ""),
        "qs": urlencode(filters),
        "can_stock": user.has_perm(VIEW),
        "can_ledger": True,
        "can_orders": user.has_perm("orders.view_order"),
    }


@panel_view(LEDGER)
@require_GET
def inventory_ledger(request):
    context = _ledger_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/inventory/_ledger_results.html", context)
    return render(request, "panel/inventory/ledger.html", context)


@panel_view(VIEW, ADJUST)
@require_http_methods(["GET", "POST"])
def stock_adjust(request, variant_pk):
    variant = get_object_or_404(Variant.objects.select_related("product"), pk=variant_pk)
    params = request.POST if request.method == "POST" else request.GET
    hidden = [(key, value) for key, value in params.items() if key in LIST_PARAMS and value]
    form = StockAdjustForm(request.POST or None, variant=variant, initial={"expected": variant.stock})
    error = ""

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.adjust_stock(
                variant.pk,
                data["delta"],
                reason=normalize_fa(data["reason"]),
                by=request.user,
                expected_stock=data["expected"] if data["mode"] == "set" else None,
            )
        except StockConflict:
            variant.refresh_from_db(fields=["stock"])
            form = StockAdjustForm(variant=variant, initial={"expected": variant.stock})
            error = f"موجودی هم‌زمان تغییر کرد یا کافی نیست؛ موجودی فعلی {to_fa_digits(variant.stock)} است"
        else:
            audit.log(request.user, variant, audit.CHANGE, f"تغییر موجودی {variant.sku}: {data['delta']:+d}")
            if not request.htmx:
                htmx.flash(request, "موجودی ثبت شد")
                return redirect("panel:inventory")
            context = {**_stock_context(request.POST, request.user), "reset_modal": True}
            response = render(request, "panel/inventory/_stock_results.html", context)
            htmx.toast(response, "موجودی ثبت شد")
            return htmx.close_popover(response, "stock-modal")

    if request.method == "POST" and not request.htmx:
        htmx.flash(request, error or "اطلاعات را بررسی کنید", "error")
        return redirect("panel:inventory")
    response = render(
        request,
        "panel/inventory/_adjust_form.html",
        {
            "form": form,
            "variant": variant,
            "error": error,
            "hidden": hidden,
            "action": reverse("panel:stock_adjust", args=[variant.pk]),
        },
    )
    if request.method == "POST":
        retarget(response, "#stock-modal-body")
        reswap(response, "innerHTML")
    return response
```

### قالب‌ها (`templates/panel/inventory/`)

**`_tabs.html`**

```html
<div role="tablist" class="tabs tabs-border">
  {% if can_stock %}<a role="tab" href="{% url 'panel:inventory' %}" class="tab{% if active == 'stock' %} tab-active{% endif %}">وضعیت انبار</a>{% endif %}
  {% if can_ledger %}<a role="tab" href="{% url 'panel:inventory_ledger' %}" class="tab{% if active == 'ledger' %} tab-active{% endif %}">دفتر گردش موجودی</a>{% endif %}
</div>
```

**`list.html`**

```html
{% extends "panel/shell.html" %}
{% block title %}انبار{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="انبار" %}
    <span id="inventory-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  {% include "panel/inventory/_tabs.html" with active="stock" %}

  <form action="{% url 'panel:inventory' %}" method="get" role="search"
        hx-get="{% url 'panel:inventory' %}" hx-target="#inventory-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-sync="this:replace" hx-indicator="#inventory-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3">
    {% if filters.product %}<input type="hidden" name="product" value="{{ filters.product }}">{% endif %}
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ q }}" placeholder="عنوان محصول یا کد کالا" class="grow text-small" autocomplete="off">
    </label>
    <select name="state" class="select h-10 w-48 text-small">
      <option value="">همه‌ی وضعیت‌ها</option>
      {% for code, label in states %}<option value="{{ code }}"{% if code == state %} selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
  </form>

  <div id="inventory-results" aria-live="polite">{% include "panel/inventory/_stock_results.html" %}</div>
</div>
<div class="modal" popover id="stock-modal"><div class="modal-box max-w-sm" id="stock-modal-body"></div></div>
{% endblock %}
```

**`_stock_results.html`**

```html
{% load core_tags panel_tags %}
<div class="flex flex-col gap-4">
  {% if product_note %}
    <div role="alert" class="alert text-small">
      <span>فقط تنوع‌های «{{ product_note|fa_text }}»</span>
      <a href="{% url 'panel:inventory' %}" class="link">نمایش همه</a>
    </div>
  {% endif %}

  {% if page_obj.object_list %}
    <div class="bg-base-100 border rounded-box overflow-x-auto">
      <table class="table table-sm">
        <thead><tr>
          <th scope="col">محصول</th><th scope="col">کد کالا</th><th scope="col">موجودی</th>
          <th scope="col">منتظران پیامک</th><th scope="col">صف «موجود شد»</th><th scope="col"><span class="sr-only">اقدام</span></th>
        </tr></thead>
        <tbody>
          {% for v in page_obj.object_list %}
            <tr class="hover:bg-base-300">
              <td>
                <div class="flex items-center gap-3 min-w-0">
                  <span class="w-10 h-10 shrink-0 rounded-lg bg-white border overflow-hidden flex items-center justify-center">
                    {% if v.product.main_image %}<img src="{{ v.product.main_image|thumb_url }}" alt="" width="40" height="40" loading="lazy" class="w-full h-full object-contain p-1">{% else %}{% icon "package" size=18 class="text-ink-3" %}{% endif %}
                  </span>
                  <span class="min-w-0 flex flex-col">
                    {% if can_open_product %}<a href="{% url 'panel:product_studio' v.product_id %}" class="text-small link link-hover line-clamp-1">{{ v.product.title|fa_text }}</a>
                    {% else %}<span class="text-small line-clamp-1">{{ v.product.title|fa_text }}</span>{% endif %}
                    <span class="text-label text-ink-3">{{ v.title|fa_text }}{% if not v.is_active %} <span class="badge badge-sm badge-soft ms-1">غیرفعال</span>{% endif %}</span>
                  </span>
                </div>
              </td>
              <td><span class="latin">{{ v.sku }}</span></td>
              <td class="whitespace-nowrap">
                {% if v.stock <= 0 %}
                  <span class="flex items-center gap-1 text-small text-ink-2">{% icon "alert-circle" size=16 class="text-ink-3" %}ناموجود</span>
                {% else %}
                  <span class="num text-small font-medium">{{ v.stock|fa_digits }}</span>
                  {% if v.stock <= low %}<span class="text-label text-ink-3 ms-2">کم‌موجود</span>{% endif %}
                {% endif %}
              </td>
              <td><span class="num">{{ v.waiting|fa_digits }}</span></td>
              <td>
                {% if v.queued %}<span class="num">{{ v.queued|fa_digits }}</span><div class="text-label text-ink-3">{{ send_hint }}</div>{% else %}<span class="text-ink-3">—</span>{% endif %}
              </td>
              <td>
                {% if can_adjust %}
                  <button type="button" popovertarget="stock-modal" class="btn btn-sm h-10 bg-base-300 border whitespace-nowrap"
                          hx-get="{% url 'panel:stock_adjust' v.pk %}?{{ qs }}&page={{ page_obj.number }}"
                          hx-target="#stock-modal-body" hx-swap="innerHTML">تغییر موجودی</button>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% include "panel/partials/_pagination.html" with target="#inventory-results" %}
  {% else %}
    {% include "partials/_empty_state.html" with title="تنوعی پیدا نشد" description="فیلترها را تغییر دهید" %}
  {% endif %}
</div>
{% if reset_modal %}<div id="stock-modal-body" class="modal-box max-w-sm" hx-swap-oob="true"></div>{% endif %}
```

**`_adjust_form.html`**

```html
{% load core_tags %}
<form method="post" action="{{ action }}" hx-post="{{ action }}" hx-target="#inventory-results" hx-swap="innerHTML"
      hx-disabled-elt="find button[type='submit']" class="flex flex-col gap-3" novalidate>
  {% csrf_token %}
  {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
  {{ form.expected }}
  <div>
    <h3 class="text-lead font-medium">تغییر موجودی</h3>
    <p class="text-small text-ink-2 mt-1"><bdi>{{ variant.product.title|fa_text }}</bdi> — {{ variant.title|fa_text }} (<span class="latin">{{ variant.sku }}</span>)</p>
    <p class="text-small mt-1">موجودی فعلی: <span class="num font-medium">{{ variant.stock|fa_digits }}</span></p>
  </div>

  {% if error %}<div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ error }}</span></div>{% endif %}
  {% for e in form.non_field_errors %}<div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ e }}</span></div>{% endfor %}

  <fieldset class="fieldset">
    <legend class="fieldset-legend text-small font-medium">نوع تغییر</legend>
    {% for radio in form.mode %}
      <label class="flex items-center gap-2 cursor-pointer min-h-10">
        <input type="radio" name="{{ radio.data.name }}" value="{{ radio.data.value }}" class="radio radio-sm"{% if radio.data.selected %} checked{% endif %}>
        <span class="text-small">{{ radio.choice_label }}</span>
      </label>
    {% endfor %}
  </fieldset>

  <fieldset class="fieldset">
    <legend class="fieldset-legend text-small font-medium">{{ form.amount.label }}</legend>
    {{ form.amount }}
    {% for e in form.amount.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ e }}</span></p>{% endfor %}
  </fieldset>

  <fieldset class="fieldset">
    <legend class="fieldset-legend text-small font-medium">{{ form.reason.label }}</legend>
    {{ form.reason }}
    {% for e in form.reason.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ e }}</span></p>{% endfor %}
    <p class="label text-label text-ink-3">مثلاً شمارش انبار، ورود کالای جدید یا کالای معیوب</p>
  </fieldset>

  <div class="flex items-center gap-2 border-t pt-3">
    <button type="submit" class="btn btn-primary flex-1 min-w-0 h-11 min-h-11">ثبت موجودی</button>
    <button type="button" popovertarget="stock-modal" popovertargetaction="hide" class="btn btn-ghost h-11 text-ink-2">انصراف</button>
  </div>
</form>
```

**`ledger.html`**

```html
{% extends "panel/shell.html" %}
{% load static %}
{% block title %}دفتر گردش موجودی{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="انبار" %}
    <span id="ledger-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  {% include "panel/inventory/_tabs.html" with active="ledger" %}

  <form action="{% url 'panel:inventory_ledger' %}" method="get" role="search"
        hx-get="{% url 'panel:inventory_ledger' %}" hx-target="#ledger-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-sync="this:replace" hx-indicator="#ledger-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3">
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ q }}" placeholder="عنوان محصول یا کد کالا" class="grow text-small" autocomplete="off">
    </label>
    <select name="reason" class="select h-10 w-40 text-small">
      <option value="">همه‌ی دلیل‌ها</option>
      {% for code, label in reasons %}<option value="{{ code }}"{% if code == reason %} selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <div class="contents" data-date-range>
      <input type="text" name="from" value="{{ date_from }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="از تاریخ" class="input h-10 w-36 num text-small">
      <input type="text" name="to" value="{{ date_to }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="تا تاریخ" class="input h-10 w-36 num text-small">
      <span class="hidden text-label text-error" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد</span>
    </div>
  </form>

  <div id="ledger-results" aria-live="polite">{% include "panel/inventory/_ledger_results.html" %}</div>
</div>
{% endblock %}
{% block extra_js %}<script src="{% static 'js/jalali_picker.js' %}" defer></script>{% endblock %}
```

**`_ledger_results.html`**

```html
{% load core_tags jalali_tags panel_tags %}
<div class="flex flex-col gap-4">
  {% if rows %}
    <div class="bg-base-100 border rounded-box overflow-x-auto">
      <table class="table table-sm">
        <thead><tr>
          <th scope="col">زمان</th><th scope="col">کالا</th><th scope="col">تغییر</th>
          <th scope="col">دلیل</th><th scope="col">یادداشت</th><th scope="col">سفارش</th>
        </tr></thead>
        <tbody>
          {% for movement, number in rows %}
            <tr class="hover:bg-base-300">
              <td class="text-ink-2 whitespace-nowrap"><span class="num">{{ movement.created_at|to_jalali }}</span></td>
              <td>
                <span class="text-small">{{ movement.variant.product.title|fa_text }}</span>
                <div class="text-label text-ink-3">{{ movement.variant.title|fa_text }} — <span class="latin">{{ movement.variant.sku }}</span></div>
              </td>
              <td class="whitespace-nowrap"><span class="num font-medium">{{ movement.delta|signed }}</span></td>
              <td class="whitespace-nowrap text-small">{{ movement.get_reason_display }}</td>
              <td class="text-small text-ink-2">{{ movement.note|fa_text }}</td>
              <td>
                {% if number %}{% if can_orders %}<a href="{% url 'panel:order_detail' number %}" class="latin link link-hover">{{ number }}</a>{% else %}<span class="latin">{{ number }}</span>{% endif %}{% endif %}
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% include "panel/partials/_pagination.html" with target="#ledger-results" %}
  {% else %}
    {% include "partials/_empty_state.html" with title="گردشی پیدا نشد" description="فیلترها را تغییر دهید" %}
  {% endif %}
</div>
```

### استودیوی محصول (تغییر کوچک)

- در `apps/panel/views/products.py`، داخل دیکشنری برگشتی `_studio_context`، بعد از `"can_delete": ...` اضافه کن: `"can_stock": user.has_perm("catalog.adjust_stock"),`
- در `templates/panel/products/_sec_variants.html`، خط اول را `{% load core_tags %}` کن. داخل حلقه‌ی `{% for variant, form in variant_forms %}` و درست قبل از `<form hx-post=...variant_edit...>` اضافه کن:

```html
        <p class="text-label text-ink-3 mb-1">موجودی «{{ variant.title|fa_text }}»: <span class="num">{{ variant.stock|fa_digits }}</span>{% if can_stock %} — <a href="{% url 'panel:inventory' %}?product={{ product.pk }}" class="link">تغییر موجودی</a>{% endif %}</p>
```

## ۷. نظرها

### `apps/panel/views/reviews.py` (جدید)

```python
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
```

### قالب‌ها (`templates/panel/reviews/` و `templates/panel/partials/`)

**`reviews/list.html`**

```html
{% extends "panel/shell.html" %}
{% block title %}نظرها{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="نظرها" %}
    <span id="reviews-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  <div id="reviews-results" aria-live="polite">{% include "panel/reviews/_list_results.html" %}</div>
</div>
{% endblock %}
```

**`reviews/_list_results.html`**

```html
{% load core_tags panel_tags %}
<div class="flex flex-col gap-4">
  <div role="tablist" class="tabs tabs-border overflow-x-auto no-scrollbar">
    {% for code, label, count in tabs %}
      <a role="tab" class="tab gap-2 whitespace-nowrap{% if code == tab %} tab-active{% endif %}" href="?tab={{ code }}"
         hx-get="?tab={{ code }}" hx-target="#reviews-results" hx-push-url="true" hx-indicator="#reviews-indicator">
        {{ label }}<span class="text-label text-ink-3 num">{{ count|fa_digits }}</span>
      </a>
    {% endfor %}
  </div>

  {% if page_obj.object_list %}
    {% if can_moderate %}
      {# the cards hold their own forms, so the checkboxes join this one with form="reviews-bulk" #}
      <form id="reviews-bulk" method="post" action="{% url 'panel:review_decide' %}" hx-post="{% url 'panel:review_decide' %}"
            hx-target="#reviews-results" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']"
            class="flex items-center justify-between gap-3">
        {% csrf_token %}
        {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
        <input type="hidden" name="action" value="approve">
        <label class="flex items-center gap-2 text-small text-ink-2 cursor-pointer min-h-10">
          <input type="checkbox" data-check-all class="checkbox checkbox-sm"><span>انتخاب همه</span>
        </label>
        <button type="submit" class="btn btn-primary h-10 min-h-10">تایید انتخاب‌شده‌ها</button>
      </form>
    {% endif %}

    <ul class="flex flex-col gap-3">
      {% for review in page_obj.object_list %}{% include "panel/reviews/_card.html" %}{% endfor %}
    </ul>
    {% include "panel/partials/_pagination.html" with target="#reviews-results" %}
  {% else %}
    {% include "partials/_empty_state.html" with title="نظری پیدا نشد" description="تب دیگری را ببینید" %}
  {% endif %}
</div>
{% if request.htmx %}{% render_sidebar oob=True %}{% endif %}
```

**`reviews/_card.html`**

```html
{% load core_tags jalali_tags panel_tags %}
<li class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
  <div class="flex items-start gap-3">
    {% if can_moderate %}<input type="checkbox" form="reviews-bulk" name="review" value="{{ review.pk }}:{{ review.updated_at|stamp }}" class="checkbox checkbox-sm mt-1 shrink-0" aria-label="انتخاب نظر">{% endif %}
    <a href="{{ review.product.get_absolute_url }}" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true"
       class="w-12 h-12 shrink-0 rounded-lg bg-white border overflow-hidden flex items-center justify-center">
      {% if review.product.main_image %}<img src="{{ review.product.main_image|thumb_url }}" alt="" width="48" height="48" loading="lazy" class="w-full h-full object-contain p-1">{% else %}{% icon "package" size=18 class="text-ink-3" %}{% endif %}
    </a>
    <div class="min-w-0 flex-1 flex flex-col gap-1">
      <a href="{{ review.product.get_absolute_url }}" target="_blank" rel="noopener" class="text-small font-medium leading-6 line-clamp-2">{{ review.product.title|fa_text }}</a>
      <span class="flex flex-wrap items-center gap-2 text-label text-ink-3">
        <bdi>{{ review.user.get_full_name|default:review.user.mobile|fa_text }}</bdi>
        {% if review.is_verified_buyer %}<span class="badge badge-sm badge-soft">خریدار این محصول</span>{% endif %}
        <span class="num">{{ review.created_at|to_jalali }}</span>
      </span>
    </div>
    <span class="flex items-center gap-2 text-small shrink-0 whitespace-nowrap"><span class="status {{ review.status|review_dot }}"></span>{{ review.get_status_display }}</span>
  </div>

  {% include "partials/_stars.html" with value=review.rating size="xs" %}
  <p class="text-small leading-7 whitespace-pre-line">{{ review.body|fa_text }}</p>
  {% if review.rejection_reason %}<p class="text-label text-ink-3">دلیل رد (داخلی): {{ review.rejection_reason|fa_text }}</p>{% endif %}
  {% if review.admin_reply %}
    <div class="bg-base-200 rounded-sm p-3 flex flex-col gap-1">
      <span class="text-label text-ink-3">پاسخ فروشگاه</span>
      <p class="text-small leading-7 whitespace-pre-line">{{ review.admin_reply|fa_text }}</p>
    </div>
  {% endif %}

  {% if can_moderate %}
    <div class="flex flex-wrap items-start gap-2 border-t pt-3">
      {% if review.status != "approved" %}
        <form method="post" action="{% url 'panel:review_decide' %}" hx-post="{% url 'panel:review_decide' %}"
              hx-target="#reviews-results" hx-swap="innerHTML" hx-disabled-elt="find button">
          {% csrf_token %}
          {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
          <input type="hidden" name="review" value="{{ review.pk }}:{{ review.updated_at|stamp }}">
          <input type="hidden" name="action" value="approve">
          <button type="submit" class="btn btn-sm h-10 bg-base-300 border">تایید و انتشار</button>
        </form>
      {% endif %}

      {% if review.status != "rejected" %}
        <details class="open:w-full">
          <summary class="btn btn-ghost btn-sm h-10 text-ink-2 list-none">رد کردن</summary>
          <form method="post" action="{% url 'panel:review_decide' %}" hx-post="{% url 'panel:review_decide' %}"
                hx-target="#reviews-results" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']"
                class="flex flex-col gap-2 mt-2">
            {% csrf_token %}
            {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
            <input type="hidden" name="review" value="{{ review.pk }}:{{ review.updated_at|stamp }}">
            <input type="hidden" name="action" value="reject">
            <input type="text" name="reason" maxlength="200" data-fa-digits autocomplete="off" class="input w-full text-small" aria-label="دلیل رد (داخلی)" placeholder="دلیل رد (داخلی، اختیاری)">
            <button type="submit" class="btn btn-sm h-10 bg-base-300 border self-start">رد کردن نظر</button>
          </form>
        </details>
      {% endif %}

      <details class="open:w-full">
        <summary class="btn btn-ghost btn-sm h-10 text-ink-2 list-none">{% if review.admin_reply %}ویرایش پاسخ{% else %}پاسخ فروشگاه{% endif %}</summary>
        <form method="post" action="{% url 'panel:review_reply' review.pk %}" hx-post="{% url 'panel:review_reply' review.pk %}"
              hx-target="#reviews-results" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']"
              class="flex flex-col gap-2 mt-2">
          {% csrf_token %}
          {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
          <textarea name="reply" rows="3" maxlength="1000" data-fa-digits class="textarea w-full text-small" aria-label="پاسخ فروشگاه">{{ review.admin_reply|fa_text }}</textarea>
          <p class="text-label text-ink-3">پاسخ فقط وقتی نظر تایید شده باشد در فروشگاه دیده می‌شود. خالی بگذارید تا پاسخ حذف شود</p>
          <button type="submit" class="btn btn-sm h-10 bg-base-300 border self-start">ذخیره‌ی پاسخ</button>
        </form>
      </details>
    </div>
  {% endif %}
</li>
```

**`partials/_review_queue.html`**

```html
{% load core_tags panel_tags %}
<section id="review-queue" class="bg-base-100 border rounded-box p-4 flex flex-col gap-3 min-h-40">
  <div class="flex items-center justify-between gap-3">
    <h2 class="text-lead font-medium">نظرهای منتظر تایید</h2>
    <a href="{% url 'panel:reviews' %}" class="text-small text-brand-ink">همه‌ی نظرها</a>
  </div>
  {% for review in review_queue %}
    <div class="flex items-start justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
      <div class="min-w-0 flex flex-col gap-1">
        <span class="text-small font-medium line-clamp-1">{{ review.product.title|fa_text }}</span>
        {% include "partials/_stars.html" with value=review.rating size="xs" %}
        <p class="text-small text-ink-2 leading-6 whitespace-pre-line">{{ review.body|fa_text }}</p>
      </div>
      {% if can_moderate %}
        <form method="post" action="{% url 'panel:review_decide' %}" hx-post="{% url 'panel:review_decide' %}"
              hx-target="#review-queue" hx-swap="outerHTML" hx-disabled-elt="find button">
          {% csrf_token %}
          <input type="hidden" name="review" value="{{ review.pk }}:{{ review.updated_at|stamp }}">
          <input type="hidden" name="action" value="approve"><input type="hidden" name="ctx" value="dashboard">
          <button type="submit" class="btn btn-sm h-10 bg-base-300 border shrink-0">تایید</button>
        </form>
      {% endif %}
    </div>
  {% empty %}
    <p class="text-small text-ink-2 py-6 text-center">نظری منتظر تایید نیست</p>
  {% endfor %}
</section>
```

**`partials/_wanted_stock.html`**

```html
{% load core_tags %}
<section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
  <div class="flex items-center justify-between gap-3">
    <h2 class="text-lead font-medium">ناموجودهای پرمتقاضی</h2>
    <a href="{% url 'panel:inventory' %}?state=out" class="text-small text-brand-ink">انبار</a>
  </div>
  {% for v in wanted %}
    <a href="{% url 'panel:inventory' %}?product={{ v.product_id }}" class="flex items-center justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
      <span class="min-w-0 flex flex-col">
        <span class="text-small line-clamp-1">{{ v.product.title|fa_text }}</span>
        <span class="text-label text-ink-3">{{ v.title|fa_text }} — <span class="latin">{{ v.sku }}</span></span>
      </span>
      <span class="text-small text-ink-2 whitespace-nowrap shrink-0"><span class="num">{{ v.waiting|fa_digits }}</span> نفر منتظر</span>
    </a>
  {% endfor %}
</section>
```

## ۸. داشبورد

**`apps/panel/views/dashboard.py`** را کامل با این جایگزین کن:

```python
from __future__ import annotations

from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.panel import queries
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services


@panel_view(authenticated_only=True)
@require_GET
def dashboard(request):
    user = request.user
    can_orders = user.has_perm("orders.view_order")
    can_reviews = user.has_perm("engagement.view_review")
    can_stock = user.has_perm("catalog.view_variant")
    context = {
        "can_orders": can_orders,
        "can_reviews": can_reviews,
        "can_stock": can_stock,
        "refunds": payment_services.refund_candidates().count() if user.has_perm("payments.view_payment") else 0,
    }
    if can_orders:
        context.update(to_ship=queries.orders_to_ship(), sales=queries.sales_last_30_days(), **queries.ship_queue(user))
    if can_reviews:
        context.update(reviews_pending=queries.reviews_pending(), **queries.review_queue(user))
    if can_stock:
        context.update(stock_alerts=queries.stock_alert_count(), wanted=queries.wanted_out_of_stock())
    return render(request, "panel/dashboard.html", context)
```

**`templates/panel/dashboard.html`** را کامل با این جایگزین کن:

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}داشبورد{% endblock %}
{% block content %}
<div class="flex flex-col gap-6">
  {% include "panel/partials/_page_heading.html" with title="داشبورد" %}

  {% if refunds %}
    <a href="{% url 'panel:payments' %}" class="alert text-small hover:bg-base-300 transition-colors">
      {% icon "alert-circle" size=18 class="text-ink-2 shrink-0" %}
      <span>{{ refunds|fa_digits }} پرداخت تاییدشده نیاز به بازگشت وجه دارد</span>
    </a>
  {% endif %}

  {% if can_orders or can_reviews or can_stock %}
    <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3" aria-label="خلاصه">
      {% if can_orders %}
        <a href="{% url 'panel:orders' %}" class="bg-base-100 border rounded-box p-4 flex flex-col gap-1 hover:bg-base-300 transition-colors">
          <span class="text-small text-ink-2">منتظر ارسال</span>
          <span class="text-title font-medium">{{ to_ship|fa_digits }}</span>
          <span class="text-label text-ink-3">پرداخت‌شده یا در حال آماده‌سازی</span>
        </a>
        <div class="bg-base-100 border rounded-box p-4 flex flex-col gap-1">
          <span class="text-small text-ink-2">فروش ۳۰ روز اخیر</span>
          <span class="text-title font-medium whitespace-nowrap">{{ sales|toman }} <span class="text-small text-ink-2 font-normal">تومان</span></span>
          <span class="text-label text-ink-3">سفارش‌های پرداخت‌شده</span>
        </div>
      {% endif %}
      {% if can_reviews %}
        <a href="{% url 'panel:reviews' %}" class="bg-base-100 border rounded-box p-4 flex flex-col gap-1 hover:bg-base-300 transition-colors">
          <span class="text-small text-ink-2">نظرهای منتظر تایید</span>
          <span class="text-title font-medium">{{ reviews_pending|fa_digits }}</span>
          <span class="text-label text-ink-3">تا تایید نشوند در فروشگاه دیده نمی‌شوند</span>
        </a>
      {% endif %}
      {% if can_stock %}
        <a href="{% url 'panel:inventory' %}?state=alert" class="bg-base-100 border rounded-box p-4 flex flex-col gap-1 hover:bg-base-300 transition-colors">
          <span class="text-small text-ink-2">ناموجود یا کم‌موجود</span>
          <span class="text-title font-medium">{{ stock_alerts|fa_digits }}</span>
          <span class="text-label text-ink-3">تنوع فعال از محصولات فعال</span>
        </a>
      {% endif %}
    </section>

    {% if can_orders %}{% include "panel/partials/_ship_queue.html" %}{% endif %}
    {% if can_reviews and review_queue %}{% include "panel/partials/_review_queue.html" %}{% endif %}
    {% if can_stock and wanted %}{% include "panel/partials/_wanted_stock.html" %}{% endif %}
  {% elif not refunds %}
    {% include "partials/_empty_state.html" with title="هنوز بخشی به حساب شما اضافه نشده" description="از مدیر کل بخواهید دسترسی‌های لازم را بدهد" %}
  {% endif %}
</div>
{% endblock %}
```

## ۹. تست‌ها

**فقط این دو فایل تست تازه بنویس و بیشتر نه.**

### `apps/catalog/tests/test_manual_stock.py`

```python
"""Manual stock changes (D43): ledger, no negative stock, compare-and-set, real restock only."""

import pytest
from django.db import transaction

from apps.catalog import stock
from apps.catalog.models import StockMovement
from apps.engagement.models import StockSubscription

pytestmark = pytest.mark.django_db


def test_change_is_logged_and_refreshes_the_product(product, django_capture_on_commit_callbacks):
    variant = product.variants.get()
    with django_capture_on_commit_callbacks(execute=True), transaction.atomic():
        stock.adjust_manual(variant.pk, -5, note="شمارش")

    variant.refresh_from_db()
    product.refresh_from_db()
    assert variant.stock == 0 and product.in_stock is False
    movement = StockMovement.objects.get(variant=variant)
    assert (movement.delta, movement.reason, movement.note) == (-5, StockMovement.REASON_MANUAL, "شمارش")


def test_never_goes_negative_and_expected_stock_is_checked(product):
    variant = product.variants.get()
    with pytest.raises(stock.StockConflict):
        stock.adjust_manual(variant.pk, -6, note="x")
    with pytest.raises(stock.StockConflict) as caught:
        stock.adjust_manual(variant.pk, 1, note="x", expected_stock=4)
    assert caught.value.current == 5
    assert not StockMovement.objects.exists()


def test_subscribers_are_marked_only_when_stock_leaves_zero(buyer, product, django_capture_on_commit_callbacks):
    variant = product.variants.get()
    sub = StockSubscription.objects.create(user=buyer, variant=variant)

    def move(delta):
        with django_capture_on_commit_callbacks(execute=True), transaction.atomic():
            stock.adjust_manual(variant.pk, delta, note="x")

    move(2)  # 5 -> 7: not a restock
    assert StockSubscription.objects.get(pk=sub.pk).restocked_at is None
    move(-7)  # -> 0
    move(4)  # 0 -> 4: a real restock
    assert StockSubscription.objects.get(pk=sub.pk).restocked_at is not None
```

### `apps/panel/tests/test_stock_reviews.py`

```python
"""Stock change and review moderation through the panel: permission, ledger, counters, stale decisions."""

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import StockMovement
from apps.engagement.models import Review
from apps.panel import queries

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-12345"


def _staff(client, mobile, *codenames):
    user = User.objects.create_user(mobile, password=PASSWORD, is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    assert client.post(reverse("panel:login"), {"mobile": mobile, "password": PASSWORD}).status_code == 302
    return user


def test_stock_change_needs_adjust_permission_and_lands_in_the_ledger(client, product):
    variant = product.variants.get()
    url = reverse("panel:stock_adjust", args=[variant.pk])
    payload = {"mode": "set", "amount": "8", "expected": str(variant.stock), "reason": "شمارش انبار"}
    staff = _staff(client, "09121110001", "view_variant")

    assert client.post(url, payload).status_code == 403

    staff.user_permissions.add(Permission.objects.get(codename="adjust_stock"))
    client.post(url, payload)
    variant.refresh_from_db()
    assert variant.stock == 8
    movement = StockMovement.objects.get(variant=variant)
    assert (movement.delta, movement.reason) == (3, StockMovement.REASON_MANUAL)
    assert "شمارش انبار" in movement.note and staff.mobile in movement.note


def test_moderation_keeps_counters_right_and_refuses_stale_decisions(client, product, buyer):
    review = Review.objects.create(user=buyer, product=product, rating=4, body="کیفیت ساخت خوب است")
    _staff(client, "09121110002", "view_review", "change_review")
    decide = reverse("panel:review_decide")
    seen = f"{review.pk}:{queries.stamp(review.updated_at)}"

    client.post(decide, {"action": "approve", "review": seen})
    review.refresh_from_db()
    product.refresh_from_db()
    assert review.status == Review.APPROVED and product.review_count == 1

    client.post(decide, {"action": "reject", "review": seen, "reason": "x"})  # the version it saw is gone
    review.refresh_from_db()
    assert review.status == Review.APPROVED

    fresh = f"{review.pk}:{queries.stamp(review.updated_at)}"
    client.post(decide, {"action": "reject", "review": fresh, "reason": "نامناسب"})
    review.refresh_from_db()
    product.refresh_from_db()
    assert review.status == Review.REJECTED and review.rejection_reason == "نامناسب"
    assert product.review_count == 0

    client.post(reverse("panel:review_reply", args=[review.pk]), {"reply": "ممنون از نظر شما"})
    review.refresh_from_db()
    assert review.admin_reply == "ممنون از نظر شما" and review.status == Review.REJECTED
```

### حذف تست‌های بی‌ارزش (چک‌های فریم‌ورک/مارک‌آپ)

بعد از حذف، importهای بلااستفاده را با `ruff check --fix` پاک کن. فقط این سه مورد را حذف کن و دنبال موارد دیگر نگرد:
- `apps/core/tests/test_core_app.py`: تابع `test_home_has_no_external_cdn_and_inactive_pages_are_404` (رشته‌گردی در HTML و ۴۰۴ فریم‌ورک).
- `apps/catalog/tests/test_views.py`: تابع‌های `test_inactive_category_is_404` و `test_search_page_and_suggest` (منطق جستجو در `test_search.py` پوشش دارد).

## ۱۰. اسناد (کوتاه، فقط همین‌ها)

- **`docs/09-panel-spec.md`:**
  - ماژول ۷: سه حالت «افزودن / کم کردن / تنظیم به عدد».
  - ماژول ۷: تخته‌ی انبار = تنوع‌های فعالِ محصولات فعال، یا همه‌ی تنوع‌های یک محصول با `?product=`.
  - ماژول ۷: فرم تغییر از مودال، و در استودیو فقط نمایش موجودی + لینک به انبار.
  - ماژول ۸: هر تصمیم نسخه‌ی دیده‌شده (`pk:stamp`) را چک می‌کند.
  - ماژول ۸: انیمیشن محو کارت حذف شد (فهرست بعد از هر تصمیم تازه می‌شود).
  - سوال باز ۲ در ۲.۱۰ را «بسته: بله، فروش و محتوا» کن.
- **`docs/02-spec.md`:** در بخش ۱۲، جمله‌ی «از P12 …» را قطعی کن (`stock` در `VariantInline` همیشه فقط‌خواندنی) و سوال باز ۸ را ببند.
- **`docs/03-data-model.md`:** یک خط «۰.۳.۱۳ (P12) — مجوز `adjust_stock` و `stock.adjust_manual` در کد» به «تغییرات» اضافه کن.
- **`docs/08-ui-modules.md`:** در ردیف `panel.js`، `[data-check-all]` را اضافه کن (چک‌باکس‌های `form="…"` بیرون از فرم را هم می‌گیرد).
- **`docs/phases/STATUS.md`:** ردیف P12 را ✅ کن و یادداشت کوتاه بنویس: تصمیم‌های بند اول بریف + سه تست حذف‌شده + «بعد از migrate باید `setup_groups` اجرا شود».

## ۱۱. پایان کار

به این ترتیب:
1. `makemigrations`
2. `pnpm run build:css`
3. `uv run python scripts/build_sprite.py`
4. `uv run ruff check . --fix`
5. `uv run ruff format .`
6. `uv run pytest apps/panel apps/catalog apps/engagement apps/core -q`

اگر چیزی شکست خورد، فقط همان را درست کن.

**گزارش پایانی (حداکثر ۱۰ خط):** چه ساخته شد، چه چیزی `[ASSUMPTION]` است، و این فهرست «چه چیزی باید دیده شود» برای من. هیچ‌کدام را خودت نگاه نکن.

**فهرست بررسی چشمی (دو تم، عرض ۳۲۰ و ۱۲۸۰):**
1. بعد از `migrate` و `setup_groups`، ورود با staff هر گروه فقط بخش‌های مجازش را در سایدبار نشان می‌دهد.
2. `/panel/inventory/`:
   - جدول و فیلترها.
   - مودال با دکمه‌ی «تغییر موجودی»: موجودی فعلی و سه حالت.
   - خطای دلیل خالی.
   - ثبت موفق: مودال بسته می‌شود، سطر به‌روز می‌شود، toast می‌آید.
   - در مودال بعدی فرمِ قبلی دیده نشود.
3. تب دفتر: علامت `+۳` و `-۲` درست و چپ‌به‌راست باشد. فیلتر تاریخ و لینک سفارش کار کند.
4. `/panel/reviews/`:
   - تب‌ها و شمارنده‌ها.
   - کارت‌ها.
   - باز و بسته شدن «رد کردن» و «پاسخ».
   - تایید تکی.
   - رد با دلیل.
   - ذخیره‌ی پاسخ.
   - انتخاب همه و تایید گروهی.
   - بج سایدبار بعد از تصمیم.
5. داشبورد: چهار کارت، بلوک نظرها با تایید سریع، بلوک ناموجودهای پرمتقاضی، ظاهر کارت‌ها در ۳۲۰.
6. ادمین → محصول → تنوع‌ها: `stock` فقط‌خواندنی است.
7. استودیوی محصول: خط موجودی و لینک «تغییر موجودی» زیر هر تنوع.