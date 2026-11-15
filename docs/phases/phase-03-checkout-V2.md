# فاز P3 — سبد، checkout، سفارش، موجودی و پرداخت

این بریف جایگزین `docs/phases/phase-03-checkout.md` می‌شود. **حساس‌ترین فاز پروژه است: پول و موجودی.** هر فاز یک نشست است. اگر نشست طولانی شد، وضعیت را در `docs/phases/STATUS.md` بنویس.

**استثنا برای این فاز:** بند «UI را در مرورگر ببین» در `CLAUDE.md` بخش ۶ اینجا اجرا **نمی‌شود**. Claude Code مرورگر باز نمی‌کند و اسکرین‌شات نمی‌گیرد. بررسی چشمی با کاربر است و فقط «فهرست بررسی چشمی» (بخش ۶) را در گزارش پایانی می‌آورد.

---

## ۰. تصمیم‌های این بریف (اختلاف با نسخه‌ی قبلی بریف و اسناد)

همه `[ASSUMPTION]` هستند و در گام ۹ در اسناد ثبت می‌شوند. هیچ `[DECIDED]` عوض نشده است (D07، D16، D20، D24، D26، D28، D29، D30، D31 سر جایشان).

| # | تصمیم | دلیل |
|---|-------|------|
| 1 | افزودن به سبد و تغییر تعداد با **JS (`MM.cart`) + `htmx.ajax`** انجام می‌شود، برای مهمان و کاربر یکسان. | قطعه‌ی `_product_detail.html` برای همه کش می‌شود و نباید وابسته به بیننده باشد. |
| 2 | `/cart/remove/` حذف شد و `set` با تعداد ۰ همان کار را می‌کند. | یک مسیر کمتر. |
| 3 | موجودی هنگام ساخت سفارش کم می‌شود (`StockMovement.reason="order"`). هنگام پرداخت **حرکت جدیدی ثبت نمی‌شود** (`sale` نداریم). | موجودی در رزرو کم شده و پرداخت آن را عوض نمی‌کند. |
| 4 | `StockMovement.order_item_id` عدد ساده می‌ماند و FK نمی‌شود. | از وابستگی چرخه‌ای مهاجرت‌های `catalog` و `orders` جلوگیری می‌شود. دفتر موجودی هم FK لازم ندارد. |
| 5 | گیرنده همان `Address.recipient_*` است و بخش جداگانه‌ی «گیرنده» نداریم. | P2 گیرنده را روی آدرس گذاشته و پیش‌فرضش خود کاربر است. |
| 6 | ایمیل در checkout گرفته نمی‌شود (در پروفایل ویرایش می‌شود). | ایمیل اختیاری است و فرم را شلوغ می‌کند. |
| 7 | `Order` بدون `placed_at` (همان `created_at`)، بدون `discount_total` (کد تخفیف خارج از v1) و بدون `customer_note`. | فیلد اضافه نمی‌سازیم. |
| 8 | `ShippingMethod` فقط فیلدهای v1 را دارد: `code`, `title`, `product_note`, `checkout_note`, `has_tracking`, `payment_mode`, `max_weight_g`, `is_active`, `sort`. | `base_cost`, `per_kg_cost`, `free_over`, `eta_*`, `provinces` وقتی روش دوم آمد اضافه می‌شوند. |
| 9 | هر کاربر **حداکثر یک سفارش `pending_payment`** دارد. سفارش جدید قبلی را لغو و موجودی‌اش را آزاد می‌کند. | رزرو دوباره‌ی موجودی برای یک سبد پیش نمی‌آید. |
| 10 | لیست سفارش‌ها فقط کارت است (بدون جدول دسکتاپ). | جدول با ۴ ستون ارزشی اضافه نمی‌کند. |
| 11 | وضعیت پرداخت `verifying` اضافه شد. | claim اتمیک قبل از verify لازم است. |
| 12 | تعداد badge سبد = **تعداد خط‌ها**، نه جمع تعدادها. | خط‌ها حداکثر ۳۰ تا هستند و badge کوچک است. |
| 13 | پایگاه‌داده‌ی تست **فایل SQLite** می‌شود. | تست رقابت واقعی با چند ترد روی SQLite درون‌حافظه معنا ندارد. |

---

## ۱. مطالعه

- `docs/02-spec.md` بخش‌های ۵، ۶، ۷ و ۸ («صفحات» و «حساب کاربری»)
- `docs/03-data-model.md` بخش‌های ۳ (`cart`، `orders`، `payments`) و ۵
- `docs/07-shipping-policy.md` بخش الف
- `docs/05-sms-templates.md` (فقط `order_paid`)
- `docs/vendors/zarinpal/zarinpal-complete-guide.md` (بخش‌های ۵ تا ۷، ۱۲، ۱۴، ۱۵)
- `docs/04` بخش‌های ۴.۱ (D28)، ۹.۳ تا ۹.۵ و ۱۰؛ `docs/08-ui-modules.md`
- اسکیل‌ها: `htmx-patterns`، `daisyui` (steps، list، alert، fieldset، join، radio)

## ۲. وابستگی‌های بیرونی (هیچ‌کدام کار را متوقف نمی‌کنند، D26)

- **مرچنت‌کد:** تا رسیدنش `ZARINPAL_SANDBOX=true` و sandbox رسمی. در DEBUG درگاه `fake` هم هست. گذار به واقعی فقط با `.env` است.
- **آدرس StartPay:** در سند vendor نیامده. آدرس‌های `https://payment.zarinpal.com/pg/StartPay/<authority>` و `https://sandbox.zarinpal.com/pg/StartPay/<authority>` از حافظه است. `[VERIFY]` قبل از پیاده‌سازی با سرویس MCP مستندات (`https://www.zarinpal.com/docs/mcp`) یا وب تطبیق بده و تناقض را در سند اصلاح کن.
- لوگوی زرین‌پال (A4): تا رسیدنش آیکون `credit-card`.
- `SMSIR_TEMPLATE_ID_ORDER_PAID` خالی یعنی `skipped_no_template`. سفارش هرگز به‌خاطر پیامک شکست نمی‌خورد.

---

## ۳. کارها

### گام ۰ — پاکسازی تست‌های بیهوده (قبل از هر کار دیگر)

این‌ها یا tautology هستند، یا فقط نام template و کلاس CSS را سنجاق می‌کنند، یا تکراری‌اند. حذف شوند و `uv run pytest` سبز بماند.

| فایل :: تست | دلیل |
|---|---|
| `accounts/tests/test_profile.py :: TestNationalCodeModelLock::test_empty_code_can_be_filled_once` | آنچه خودش گذاشته را assert می‌کند. |
| `accounts/tests/test_persian_digits.py :: test_otp_code_widget_has_maxlength_4` | یک attribute ثابت را assert می‌کند. |
| `accounts/tests/test_login_views.py :: TestVerifyCode::test_otp_step_uses_custom_digit_boxes` | نبودن چند کلاس CSS را assert می‌کند. |
| `accounts/tests/test_login_views.py :: TestPendingStep::test_resume_endpoint_is_gone` | ۴۰۴ پیش‌فرض را assert می‌کند. |
| `accounts/tests/test_addresses.py :: test_htmx_success_swaps_the_section`، `test_htmx_form_get_returns_the_form_with_the_city_hook`، `test_htmx_edit_form_includes_the_bound_city_options`، `TestAddressSetDefault::test_htmx_returns_the_section` | نام template و markup را سنجاق می‌کنند. |
| `catalog/tests/test_variant_limits.py :: test_negative_cap_fails_model_validation` | تکراری‌ی `test_variant_form_rejects_negative_cap`. |
| `catalog/tests/test_variant_limits.py :: test_product_page_renders_trust_items` | زیرمجموعه‌ی `test_editing_trust_item_refreshes_product_page`. |
| `core/tests/test_core_app.py :: test_brand_name_and_no_second_in_home_and_404` | markup و کلاس‌ها را سنجاق می‌کند. |

همچنین `test_shipping_note_comes_from_settings` در `test_variant_limits.py` در گام ۸ بازنویسی می‌شود.

### گام ۱ — زیرساخت

**۱.۱ تنظیمات**

`config/settings/base.py`: به `INSTALLED_APPS` اضافه شود: `"apps.cart"`, `"apps.orders"`, `"apps.payments"`.

`config/settings/test.py` (انتهای فایل):

```python
# File-based test DB: concurrency tests need real SQLite locking (in-memory shared cache behaves differently).
DATABASES = {"default": {**DATABASES["default"], "TEST": {"NAME": BASE_DIR / "test_db.sqlite3"}}}  # noqa: F405
```

`.gitignore`: خط `test_db.sqlite3*` اضافه شود.

`config/urls.py` (قبل از `geo/`):

```python
(path("", include("apps.cart.urls")),)
(path("", include("apps.orders.urls")),)
(path("payments/", include("apps.payments.urls")),)
```

**۱.۲ `apps/core/http.py`** (تابع `_client_ip` از `accounts/views.py` به اینجا منتقل می‌شود)

```python
"""Request helpers shared by views."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str | None:
    remote = (request.META.get("REMOTE_ADDR") or "").strip()
    if remote and remote in getattr(settings, "TRUSTED_PROXY_IPS", ()):
        x_real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
        if x_real:
            return x_real
        first = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        if first:
            return first
    return remote or None
```

در `accounts/views.py` تابع محلی حذف و `from apps.core.http import client_ip` جایگزین شود. تنها استفاده در `otp_request_view` است.

**۱.۳ `apps/core/decorators.py`**

```python
from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django_htmx.http import HttpResponseClientRedirect


def login_required_htmx(view):
    """Like login_required, but HTMX requests get HX-Redirect instead of a swapped login page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)
        response = redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return HttpResponseClientRedirect(response.url) if request.htmx else response

    return wrapper
```

**۱.۴ `apps/accounts/services.py`** (منطق ساخت آدرس برای استفاده‌ی مشترک accounts و checkout)

```python
from __future__ import annotations

from django.db import transaction

from apps.accounts.models import Address


def save_new_address(user, form) -> Address:
    """Save a validated AddressForm for `user`, keeping the one-default-per-user invariant."""
    address = form.save(commit=False)
    address.user = user
    active = Address.objects.filter(user=user, deleted_at__isnull=True)
    with transaction.atomic():
        address.is_default = form.cleaned_data["is_default"] or not active.exists()
        if address.is_default:
            active.update(is_default=False)
        address.save()
    return address
```

در `accounts/views.py::address_create` بلوک `with transaction.atomic(): ...` با `save_new_address(request.user, form)` عوض شود. رفتار و تست‌های موجود نباید تغییر کنند.

**۱.۵ context processor** — در `apps/core/context_processors.py` مقدار `"cart_count": 0` و کامنت آن با این جایگزین شود:

```python
    from apps.cart.services import count as cart_count
    ...
        "cart_count": cart_count(getattr(request, "user", None)),
```

(import داخل تابع، مثل `menu_categories`)

**۱.۶ `base.html`**

- تگ `<body>`: صفت `data-auth="{% if user.is_authenticated %}1{% else %}0{% endif %}"` اضافه شود.
- بعد از `shell.js`: `<script src="{% static 'js/mm/cart.js' %}" defer></script>`

**۱.۷ لینک‌ها** (`#cart` و `#orders` فعلی)

- `_header.html` (موبایل و دسکتاپ) و `_dock.html`: `href="#cart"` ← `{% url 'cart:detail' %}`
- `_header.html`: `href="#orders"` ← `{% url 'orders:list' %}`
- `_account_nav.html`: یک تب سوم «سفارش‌ها» (`orders:list`، `active == 'orders'`) اضافه شود.

**۱.۸ sprite** — آیکون‌های جدید: `trash-2`, `minus`, `credit-card` (و `plus`, `lock`, `check`, `info`, `alert-circle`, `shopping-cart`, `image`, `truck`, `package`). بعد از نوشتن قالب‌ها `make sprite` اجرا شود و خروجی خطا نداشته باشد.

---

### گام ۲ — موجودی (`apps/catalog/stock.py`)

تنها محل مجاز برای `update()` خام روی `Variant` (و شمارنده‌های `Product`) بیرون از `models.py`. در `apps/catalog/tests/test_architecture.py` مسیر `"apps/catalog/stock.py"` به `ALLOWED_FILES` اضافه شود.

```python
"""Atomic stock changes (CLAUDE.md §4). Callers must already be inside transaction.atomic()."""

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import F

from apps.catalog.models import Product, StockMovement, Variant


class InsufficientStock(Exception):
    def __init__(self, variant_id: int):
        super().__init__(f"Not enough stock for variant {variant_id}")
        self.variant_id = variant_id


def decrement(variant_id: int, qty: int, *, reason: str, order_item_id: int | None = None, note: str = "") -> None:
    updated = Variant.objects.filter(pk=variant_id, is_active=True, stock__gte=qty).update(stock=F("stock") - qty)
    if updated != 1:
        raise InsufficientStock(variant_id)
    StockMovement.objects.create(
        variant_id=variant_id, delta=-qty, reason=reason, order_item_id=order_item_id, note=note
    )


def increment(variant_id: int, qty: int, *, reason: str, order_item_id: int | None = None, note: str = "") -> None:
    Variant.objects.filter(pk=variant_id).update(stock=F("stock") + qty)
    StockMovement.objects.create(
        variant_id=variant_id, delta=qty, reason=reason, order_item_id=order_item_id, note=note
    )


def refresh_products(product_ids: Iterable[int]) -> None:
    """Recompute aggregates after stock moves; cache rev only bumps when in_stock flips (docs/03 §5)."""
    for product in Product.objects.filter(pk__in=set(product_ids)):
        product.refresh_aggregates()


def add_purchases(qty_by_product: dict[int, int]) -> None:
    """COUNTER fields: F() writes, no invalidation. P4's recount_purchases owns the 30-day window."""
    for product_id, qty in qty_by_product.items():
        Product.objects.filter(pk=product_id).update(
            purchase_count_total=F("purchase_count_total") + qty,
            purchase_count_30d=F("purchase_count_30d") + qty,
        )
```

در `apps/catalog/admin.py` انتهای `ProductAdmin.save_related` اضافه شود (طبق `07`: وزن خالی هشدار می‌گیرد و سقف وزن برایش اعمال نمی‌شود):

```python
        if product.variants.filter(is_active=True, weight_g=0).exists():
            messages.warning(request, "وزن برخی تنوع‌ها صفر است؛ سقف وزن ارسال برای آن‌ها بررسی نمی‌شود.")
```

---

### گام ۳ — اپ `cart`

ساختار: `apps/cart/{__init__,apps,models,services,views,urls}.py` و `tests/__init__.py`.

**`apps.py`**: `name = "apps.cart"`, `verbose_name = "سبد خرید"`.

**`models.py`**

```python
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")


class CartItem(TimeStampedModel):
    """Only (variant, qty): prices and stock are always re-read (D16)."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.Variant", on_delete=models.CASCADE, related_name="+")
    qty = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "variant"], name="uniq_cart_variant")]
```

**`services.py`**

```python
"""Cart rules (docs/02 §5, D29). The server re-resolves every variant on every read."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from django.db import transaction

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, Variant
from apps.core.cache import safe_cache_delete, safe_cache_get, safe_cache_set
from apps.core.text import to_fa_text

MAX_LINES = 30
MAX_QTY = 999
COUNT_TTL = 60 * 60 * 24


class CartError(Exception):
    """A user-facing reason a cart change was refused."""


@dataclass(frozen=True)
class Line:
    variant: Variant
    qty: int  # what the customer will actually get (already clamped when available)
    requested: int  # what is stored / was asked for
    available: bool

    @property
    def total(self) -> int:
        return self.variant.price * self.qty if self.available else 0

    @property
    def reduced(self) -> bool:
        return self.available and self.qty < self.requested


@dataclass(frozen=True)
class Summary:
    items_total: int
    weight_g: int
    has_unavailable: bool


def _sellable(variant: Variant) -> bool:
    return variant.is_active and variant.product.status == Product.STATUS_ACTIVE and variant.max_orderable > 0


def _to_int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def parse_items(raw: str | None) -> list[tuple[int, int]]:
    """Parse the guest cart JSON `[{"v": id, "q": qty}]`; junk is dropped, duplicates keep the max."""
    try:
        data = json.loads(raw or "[]")
    except ValueError:
        return []
    pairs: dict[int, int] = {}
    for entry in data if isinstance(data, list) else []:
        if isinstance(entry, dict):
            variant_id, qty = _to_int(entry.get("v")), _to_int(entry.get("q"))
            if variant_id > 0 and qty > 0:
                pairs[variant_id] = max(pairs.get(variant_id, 0), min(qty, MAX_QTY))
    return list(pairs.items())[:MAX_LINES]


def resolve_lines(pairs: list[tuple[int, int]]) -> list[Line]:
    variants = Variant.objects.filter(pk__in=[v for v, _ in pairs]).select_related(
        "product__brand", "product__main_image"
    )
    by_id = {variant.pk: variant for variant in variants}
    lines = []
    for variant_id, requested in pairs:
        variant = by_id.get(variant_id)
        if variant is None:  # deleted variant: silently dropped
            continue
        sellable = _sellable(variant)
        qty = min(requested, variant.max_orderable) if sellable else requested
        lines.append(Line(variant, qty, requested, sellable))
    return lines


def notices_for(lines: list[Line]) -> list[str]:
    return [
        to_fa_text(f"تعداد «{line.variant.product.title}» به {line.qty} عدد کاهش یافت (حداکثر مجاز در هر سفارش)")
        for line in lines
        if line.reduced
    ]


def summarize(lines: list[Line]) -> Summary:
    ok = [line for line in lines if line.available]
    return Summary(
        items_total=sum(line.total for line in ok),
        weight_g=sum(line.variant.weight_g * line.qty for line in ok),
        has_unavailable=len(ok) != len(lines),
    )


def fingerprint(lines: list[Line]) -> str:
    """What the customer saw: variant, qty and unit price. Checkout refuses to order if it changed."""
    raw = ";".join(
        f"{line.variant.pk}:{line.qty}:{line.variant.price}"
        for line in sorted((line for line in lines if line.available), key=lambda line: line.variant.pk)
    )
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


# --- server cart ----------------------------------------------------------


def get_cart(user) -> Cart:
    return Cart.objects.get_or_create(user=user)[0]


def count(user) -> int:
    if user is None or not user.is_authenticated:
        return 0
    key = f"cart_count:{user.pk}"
    cached = safe_cache_get(key)
    if isinstance(cached, int):
        return cached
    value = CartItem.objects.filter(cart__user=user).count()
    safe_cache_set(key, value, COUNT_TTL)
    return value


def bust_count(user_id: int) -> None:
    safe_cache_delete(f"cart_count:{user_id}")


def normalize(cart: Cart) -> tuple[list[Line], list[str]]:
    """Resolve the stored cart and persist clamped quantities (idempotent)."""
    pairs = list(cart.items.order_by("pk").values_list("variant_id", "qty"))
    lines = resolve_lines(pairs)
    for line in lines:
        if line.reduced:
            cart.items.filter(variant=line.variant).update(qty=line.qty)
    bust_count(cart.user_id)
    return lines, notices_for(lines)


def set_quantity(user, variant_id: int, qty: int) -> str:
    """Absolute quantity; 0 removes. Returns a notice ('' if none). Raises CartError."""
    qty = max(0, min(int(qty), MAX_QTY))
    with transaction.atomic():
        cart = get_cart(user)
        existing = cart.items.filter(variant_id=variant_id).first()
        notice = ""
        if qty == 0:
            if existing:
                existing.delete()
        else:
            variant = Variant.objects.select_related("product").filter(pk=variant_id).first()
            if variant is None or not _sellable(variant):
                raise CartError("این کالا در حال حاضر موجود نیست")
            if existing is None and cart.items.count() >= MAX_LINES:
                raise CartError(to_fa_text(f"سبد خرید حداکثر {MAX_LINES} قلم کالا دارد"))
            final = min(qty, variant.max_orderable)
            CartItem.objects.update_or_create(cart=cart, variant=variant, defaults={"qty": final})
            if final < qty:
                notice = to_fa_text(f"حداکثر {variant.max_orderable} عدد در هر سفارش")
    bust_count(user.pk)
    return notice


def add_one(user, variant_id: int) -> str:
    current = CartItem.objects.filter(cart__user=user, variant_id=variant_id).values_list("qty", flat=True).first() or 0
    return set_quantity(user, variant_id, current + 1)


def merge_guest_items(user, pairs: list[tuple[int, int]]) -> None:
    """Idempotent merge: qty = max(local, server), clamped to max_orderable. Never summed."""
    if not pairs:
        return
    resolved = {line.variant.pk: line for line in resolve_lines(pairs)}
    with transaction.atomic():
        cart = get_cart(user)
        existing = dict(cart.items.values_list("variant_id", "qty"))
        for variant_id, qty in pairs:
            line = resolved.get(variant_id)
            if line is None or not line.available:
                continue
            if variant_id not in existing and len(existing) >= MAX_LINES:
                continue
            target = min(max(qty, existing.get(variant_id, 0)), line.variant.max_orderable)
            if existing.get(variant_id) != target:
                CartItem.objects.update_or_create(cart=cart, variant=line.variant, defaults={"qty": target})
                existing[variant_id] = target
    bust_count(user.pk)
```

**`views.py`**

```python
from __future__ import annotations

import json

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django_htmx.http import trigger_client_event

from apps.cart import services
from apps.core.decorators import login_required_htmx
from apps.orders.shipping import default_method


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _context(lines, notices, *, guest: bool) -> dict:
    return {
        "lines": lines,
        "notices": notices,
        "summary": services.summarize(lines),
        "method": default_method(),
        "guest": guest,
        "normalized": json.dumps([{"v": line.variant.pk, "q": line.qty} for line in lines]),
    }


def _announce(response, count: int, message: str = "", ok: bool = True):
    trigger_client_event(response, "cart:changed", {"count": count, "message": message, "ok": ok})
    return response


@require_GET
def detail_view(request):
    if request.user.is_authenticated:
        lines, notices = services.normalize(services.get_cart(request.user))
        context = _context(lines, notices, guest=False)
    else:
        context = {"guest": True}
    return render(request, "pages/cart.html", context)


@require_POST
def render_view(request):
    """Guest cart: price/stock/limits for the localStorage items. Nothing is written."""
    lines = services.resolve_lines(services.parse_items(request.POST.get("items")))
    response = render(request, "partials/_cart_content.html", _context(lines, services.notices_for(lines), guest=True))
    return _announce(response, len(lines))


@login_required_htmx
@require_POST
def add_view(request):
    try:
        message, ok = services.add_one(request.user, _int(request.POST.get("variant_id"))), True
    except services.CartError as exc:
        message, ok = str(exc), False
    return _announce(HttpResponse(status=204), services.count(request.user), message, ok)


@login_required_htmx
@require_POST
def set_view(request):
    try:
        message, ok = (
            services.set_quantity(request.user, _int(request.POST.get("variant_id")), _int(request.POST.get("qty"))),
            True,
        )
    except services.CartError as exc:
        message, ok = str(exc), False
    lines, notices = services.normalize(services.get_cart(request.user))
    response = render(request, "partials/_cart_content.html", _context(lines, notices, guest=False))
    return _announce(response, len(lines), message, ok)


@login_required_htmx
@require_POST
def sync_view(request):
    services.merge_guest_items(request.user, services.parse_items(request.POST.get("items")))
    return _announce(HttpResponse(status=204), services.count(request.user))
```

**`urls.py`** (`app_name = "cart"`)

```python
urlpatterns = [
    path("cart/", views.detail_view, name="detail"),
    path("cart/render/", views.render_view, name="render"),
    path("cart/add/", views.add_view, name="add"),
    path("cart/set/", views.set_view, name="set"),
    path("cart/sync/", views.sync_view, name="sync"),
]
```

**هوک ورود** — در `accounts/views.py::otp_verify_view` بعد از `login(...)` و `_forget_pending` (جایگزین کامنت «Cart merge hook»):

```python
    try:
        cart_services.merge_guest_items(user, cart_services.parse_items(request.POST.get("guest_cart")))
    except Exception:  # a cart problem must never block login
        logger.exception("Guest cart merge failed for user %s", user.pk)
```

(import `from apps.cart import services as cart_services` و `import logging` / `logger` اضافه شود.) فیلد `guest_cart` را `cart.js` به درخواست تایید اضافه می‌کند (پایین‌تر). با این کار سبد قبل از رسیدن به `/checkout/` ادغام شده است و race وجود ندارد.

---

### گام ۴ — اپ `orders`

ساختار: `apps/orders/{__init__,apps,models,shipping,forms,services,views,urls,admin}.py`، `management/commands/expire_orders.py` و `tests/`.

**`models.py`**

```python
from __future__ import annotations

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ShippingMethod(TimeStampedModel):
    PAYMENT_PREPAID = "prepaid"
    PAYMENT_COLLECT = "collect"
    PAYMENT_CHOICES = [(PAYMENT_PREPAID, "کرایه در سایت"), (PAYMENT_COLLECT, "پس‌کرایه")]

    code = models.SlugField(max_length=32, unique=True, verbose_name="کد")
    title = models.CharField(max_length=120, verbose_name="عنوان")
    product_note = models.CharField(max_length=200, blank=True, verbose_name="متن صفحه‌ی محصول")
    checkout_note = models.CharField(max_length=300, blank=True, verbose_name="متن checkout")
    has_tracking = models.BooleanField(default=True, verbose_name="با کد رهگیری؟")
    payment_mode = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_COLLECT, verbose_name="نحوه‌ی پرداخت کرایه"
    )
    max_weight_g = models.PositiveIntegerField(null=True, blank=True, verbose_name="سقف وزن سفارش (گرم)")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "روش ارسال"
        verbose_name_plural = "روش‌های ارسال"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        transaction.on_commit(_bump_detail_pages)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        transaction.on_commit(_bump_detail_pages)
        return result


def _bump_detail_pages() -> None:
    # The product page embeds the shipping text, and it is cached under the site-wide trust revision.
    from apps.marketing.cache import bump_trust_revision

    bump_trust_revision()


STATUS_DOT = {  # docs/04 §9.4
    "pending_payment": "status-warning",
    "paid": "status-info",
    "processing": "status-info",
    "shipped": "status-info",
    "delivered": "status-success",
    "cancelled": "status-error",
    "expired": "status-neutral",
    "refunded": "status-neutral",
}


class Order(TimeStampedModel):
    PENDING = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    STATUS_CHOICES = [
        (PENDING, "در انتظار پرداخت"),
        (PAID, "پرداخت‌شده"),
        (PROCESSING, "در حال آماده‌سازی"),
        (SHIPPED, "ارسال‌شده"),
        (DELIVERED, "تحویل‌شده"),
        (CANCELLED, "لغوشده"),
        (EXPIRED, "منقضی‌شده"),
        (REFUNDED, "بازگشت وجه"),
    ]

    number = models.CharField(max_length=16, unique=True, verbose_name="شماره سفارش")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders", verbose_name="کاربر"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, verbose_name="وضعیت")

    items_total = models.BigIntegerField(verbose_name="جمع کالاها (تومان)")
    shipping_cost = models.BigIntegerField(default=0, verbose_name="هزینه‌ی ارسال (تومان)")
    payable = models.BigIntegerField(verbose_name="مبلغ قابل پرداخت (تومان)")

    buyer_name = models.CharField(max_length=170, verbose_name="نام خریدار")
    buyer_mobile = models.CharField(max_length=11, verbose_name="موبایل خریدار")
    buyer_national_code = models.CharField(max_length=10, verbose_name="کد ملی خریدار")
    buyer_email = models.EmailField(blank=True, verbose_name="ایمیل خریدار")

    recipient_name = models.CharField(max_length=120, verbose_name="نام گیرنده")
    recipient_mobile = models.CharField(max_length=11, verbose_name="موبایل گیرنده")
    province_name = models.CharField(max_length=80, verbose_name="استان")
    city_name = models.CharField(max_length=100, verbose_name="شهر")
    address_text = models.TextField(verbose_name="آدرس")
    plate = models.CharField(max_length=20, verbose_name="پلاک")
    unit = models.CharField(max_length=20, blank=True, verbose_name="واحد")
    postal_code = models.CharField(max_length=10, verbose_name="کدپستی")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    shipping_method = models.ForeignKey(
        ShippingMethod, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    shipping_method_title = models.CharField(max_length=120, verbose_name="روش ارسال")
    shipping_payment_mode = models.CharField(max_length=10, verbose_name="نحوه‌ی پرداخت کرایه")
    tracking_code = models.CharField(max_length=64, blank=True, verbose_name="کد رهگیری")

    reserved_until = models.DateTimeField(null=True, blank=True, verbose_name="رزرو تا")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پرداخت")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="order_user_created_idx"),
            models.Index(fields=["status", "reserved_until"], name="order_status_reserved_idx"),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def status_dot(self) -> str:
        return STATUS_DOT[self.status]

    @property
    def can_pay_now(self) -> bool:
        return self.status == self.PENDING and self.reserved_until is not None and self.reserved_until > timezone.now()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", null=True, on_delete=models.SET_NULL, related_name="+")
    variant = models.ForeignKey("catalog.Variant", null=True, on_delete=models.SET_NULL, related_name="+")
    product_title = models.CharField(max_length=255)
    variant_title = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    unit_price = models.BigIntegerField()
    qty = models.PositiveSmallIntegerField()
    image_path = models.CharField(max_length=300, blank=True)
    warranty_text = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["pk"]

    @property
    def line_total(self) -> int:
        return self.unit_price * self.qty

    @property
    def image_url(self) -> str:
        return f"{settings.MEDIA_URL}{self.image_path}" if self.image_path else ""


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
```

بعد از `makemigrations`، مهاجرت داده‌ی **`orders/migrations/0002_seed_shipping_method.py`** دستی اضافه شود:

```python
from django.db import migrations


def seed(apps, schema_editor):
    ShippingMethod = apps.get_model("orders", "ShippingMethod")
    ShippingMethod.objects.get_or_create(
        code="tipax",
        defaults={
            "title": "ارسال با تیپاکس",
            "product_note": "ارسال با تیپاکس به سراسر کشور؛ کرایه هنگام تحویل به پیک پرداخت می‌شود.",
            "checkout_note": "کرایه‌ی ارسال هنگام تحویل بار به پیک تیپاکس پرداخت می‌شود و جزو مبلغ این پرداخت نیست.",
            "has_tracking": True,
            "payment_mode": "collect",
            "max_weight_g": 100000,  # [VERIFY] Tipax heavy/bulky class tops out at 100 kg (docs/vendors/tipax §13.20)
            "sort": 0,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
```

**`shipping.py`**

```python
from __future__ import annotations

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod


def default_method() -> ShippingMethod | None:
    return ShippingMethod.objects.filter(is_active=True).order_by("sort", "pk").first()


def product_page_note() -> str:
    method = default_method()
    return method.product_note if method and method.product_note else SiteSettings.get_solo().shipping_note
```

در `apps/catalog/views.py` هر دو جا (`_product_context` و `variant_panel_view`) مقدار `"shipping_note": SiteSettings.get_solo().shipping_note` با `"shipping_note": product_page_note()` عوض شود. import محلی داخل تابع: `from apps.orders.shipping import product_page_note`.

**`forms.py`**

```python
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.core.text import normalize_fa
from apps.core.validators import validate_national_code
from apps.core.widgets import FaDigitsInput

FORM_ID = "checkout-form"
_PROFILE_FIELDS = ("first_name", "last_name", "national_code")


class CheckoutBuyerForm(forms.Form):
    """Only the profile fields that are still empty (D07). A filled field is absent, so it can never be overwritten."""

    first_name = forms.CharField(
        max_length=80,
        label="نام",
        widget=forms.TextInput(attrs={"class": "input w-full", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=80,
        label="نام خانوادگی",
        widget=forms.TextInput(attrs={"class": "input w-full", "autocomplete": "family-name"}),
    )
    national_code = forms.CharField(
        max_length=10,
        label="کد ملی",
        widget=FaDigitsInput(attrs={"class": "input w-full text-end num", "maxlength": "10", "data-digits-only": "1"}),
    )
    national_code_confirm = forms.BooleanField(
        required=False,
        label="از درستی کد ملی مطمئن هستم و می‌دانم بعد از ثبت قابل تغییر نیست",
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-sm mt-0.5"}),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        for name in _PROFILE_FIELDS:
            if getattr(user, name):
                del self.fields[name]
        if "national_code" not in self.fields:
            self.fields.pop("national_code_confirm", None)
        for field in self.fields.values():
            field.widget.attrs["form"] = FORM_ID  # inputs live outside the <form> element (nested forms are invalid)

    def clean_first_name(self) -> str:
        return normalize_fa(self.cleaned_data["first_name"])

    def clean_last_name(self) -> str:
        return normalize_fa(self.cleaned_data["last_name"])

    def clean_national_code(self) -> str:
        try:
            return validate_national_code(self.cleaned_data["national_code"])
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("national_code") and not cleaned.get("national_code_confirm"):
            self.add_error("national_code", "برای ثبت کد ملی، تایید قیدشده را علامت بزنید")
        return cleaned

    def apply_to(self, user) -> None:
        present = [name for name in _PROFILE_FIELDS if name in self.fields]
        for name in present:
            setattr(user, name, self.cleaned_data[name])
        if present:
            user.save(update_fields=present)  # User.save enforces the D20 lock
```

**`services.py`**

```python
"""Order lifecycle: place, expire, release stock. Money and stock rules live here (docs/02 §7)."""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.cart import services as cart_services
from apps.catalog import stock
from apps.catalog.models import StockMovement
from apps.orders.models import Order, OrderItem, OrderStatusLog
from apps.payments.models import Payment

logger = logging.getLogger(__name__)

ORDER_RESERVE = timedelta(minutes=30)  # C5 [ASSUMPTION]
PAYMENT_GRACE = timedelta(minutes=20)  # reservation floor while the customer is at the bank

CHANGED = "قیمت یا موجودی برخی کالاها تغییر کرده است. خلاصه‌ی سفارش را بررسی و دوباره تایید کنید"


class CheckoutError(Exception):
    """The order cannot be placed. `changed=True` means what is on screen is stale."""

    def __init__(self, message: str, *, changed: bool = False):
        super().__init__(message)
        self.changed = changed


def new_number() -> str:
    while True:  # inside an IMMEDIATE transaction: no concurrent writer can take the same number
        number = f"ML-{secrets.randbelow(10**8):08d}"
        if not Order.objects.filter(number=number).exists():
            return number


def log(order_id: int, from_status: str, to_status: str, note: str = "", by=None) -> None:
    OrderStatusLog.objects.create(
        order_id=order_id, from_status=from_status, to_status=to_status, note=note, by_user=by
    )


def transition(order_id: int, *, expected: str, to: str, note: str = "", by=None, **fields) -> bool:
    """Conditional status change: True only for the caller that actually moved it."""
    updated = Order.objects.filter(pk=order_id, status=expected).update(status=to, updated_at=timezone.now(), **fields)
    if updated:
        log(order_id, expected, to, note, by)
    return bool(updated)


def _image_path(product) -> str:
    image = product.main_image
    if image is None:
        return ""
    if image.widths:
        return image.widths[min(image.widths, key=int)]
    return image.image.name if image.image else ""


def release_stock(order: Order, reason: str) -> None:
    product_ids = []
    for item in order.items.exclude(variant=None):
        stock.increment(item.variant_id, item.qty, reason=reason, order_item_id=item.pk, note=order.number)
        product_ids.append(item.product_id)
    stock.refresh_products(p for p in product_ids if p)


def reserve_again(order: Order) -> bool:
    """Late payment on an expired order: take the stock back, or report that it is gone."""
    if order.items.filter(variant=None).exists():
        return False
    try:
        with transaction.atomic():
            for item in order.items.all():
                stock.decrement(
                    item.variant_id,
                    item.qty,
                    reason=StockMovement.REASON_ORDER,
                    order_item_id=item.pk,
                    note="late payment",
                )
    except stock.InsufficientStock:
        return False
    stock.refresh_products(item.product_id for item in order.items.all() if item.product_id)
    return True


def cancel_pending(order: Order, *, reason: str) -> bool:
    if not transition(
        order.pk,
        expected=Order.PENDING,
        to=Order.CANCELLED,
        note=reason,
        cancelled_at=timezone.now(),
        cancel_reason=reason,
    ):
        return False
    order.payments.filter(status__in=[Payment.INITIATED, Payment.REDIRECTED]).update(status=Payment.CANCELLED)
    release_stock(order, StockMovement.REASON_CANCEL)
    return True


def expire_order(order_id: int) -> bool:
    """Idempotent. Skips orders whose payment is being verified right now."""
    with transaction.atomic():
        order = Order.objects.filter(pk=order_id, status=Order.PENDING, reserved_until__lt=timezone.now()).first()
        if order is None or order.payments.filter(status=Payment.VERIFYING).exists():
            return False
        if not transition(order.pk, expected=Order.PENDING, to=Order.EXPIRED, note="reservation expired"):
            return False
        release_stock(order, StockMovement.REASON_EXPIRE)  # same transaction as the status flip: released exactly once
    return True


def place_order(*, user, address, method, buyer_form, seen_fingerprint: str) -> Order:
    """Revalidate everything from the database, reserve stock atomically, snapshot the order."""
    try:
        with transaction.atomic():
            lines, _ = cart_services.normalize(cart_services.get_cart(user))
            summary = cart_services.summarize(lines)
            if not lines:
                raise CheckoutError("سبد خرید خالی است")
            if summary.has_unavailable:
                raise CheckoutError("کالای ناموجود را از سبد خرید حذف کنید", changed=True)
            if cart_services.fingerprint(lines) != seen_fingerprint:
                raise CheckoutError(CHANGED, changed=True)
            if method.max_weight_g and summary.weight_g > method.max_weight_g:
                raise CheckoutError("برای ارسال این سفارش لطفاً با پشتیبانی تماس بگیرید")

            for pending in Order.objects.filter(user=user, status=Order.PENDING):
                if pending.payments.filter(status=Payment.VERIFYING).exists():
                    raise CheckoutError("پرداخت قبلی شما در حال بررسی است؛ چند دقیقه بعد دوباره تلاش کنید")
                cancel_pending(pending, reason="superseded")

            if buyer_form is not None:
                buyer_form.apply_to(user)
            if not (user.first_name and user.last_name and user.national_code):
                raise CheckoutError("اطلاعات خریدار را کامل کنید")

            order = Order.objects.create(
                number=new_number(),
                user=user,
                items_total=summary.items_total,
                shipping_cost=0,  # collect mode (07): the customer pays Tipax on delivery
                payable=summary.items_total,
                buyer_name=user.get_full_name(),
                buyer_mobile=user.mobile,
                buyer_national_code=user.national_code,
                buyer_email=user.email,
                recipient_name=address.recipient_name,
                recipient_mobile=address.recipient_mobile,
                province_name=address.province.name,
                city_name=address.city.name,
                address_text=address.address_text,
                plate=address.plate,
                unit=address.unit,
                postal_code=address.postal_code,
                lat=address.lat,
                lng=address.lng,
                shipping_method=method,
                shipping_method_title=method.title,
                shipping_payment_mode=method.payment_mode,
                reserved_until=timezone.now() + ORDER_RESERVE,
            )
            for line in lines:
                variant, product = line.variant, line.variant.product
                item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    variant=variant,
                    product_title=product.title,
                    variant_title=variant.title,
                    sku=variant.sku,
                    unit_price=variant.price,
                    qty=line.qty,
                    image_path=_image_path(product),
                    warranty_text=product.warranty_text,
                )
                try:
                    stock.decrement(
                        variant.pk,
                        line.qty,
                        reason=StockMovement.REASON_ORDER,
                        order_item_id=item.pk,
                        note=order.number,
                    )
                except stock.InsufficientStock as exc:
                    raise CheckoutError(CHANGED, changed=True) from exc
            stock.refresh_products(line.variant.product_id for line in lines)
            log(order.pk, "", Order.PENDING, "created")
    except DjangoValidationError as exc:  # the D20 national-code lock raised by User.save()
        raise CheckoutError("اطلاعات خریدار را کامل و درست وارد کنید") from exc
    return order
```

نکته‌ها: سبد بعد از ساخت سفارش **خالی نمی‌شود** (فقط بعد از پرداخت موفق، طبق `02` بخش ۷). پیامک و درگاه هیچ‌کدام داخل `place_order` نیستند.

---

### ادامه‌ی گام ۴ — `orders`: view، url، ادمین، دستور، مهاجرت

**`apps.py`** برای هر سه اپ جدید مثل بقیه: `default_auto_field`، `name = "apps.<app>"`، `verbose_name` (سبد خرید / سفارش‌ها / پرداخت‌ها).

**`apps/orders/views.py`**

```python
"""Checkout, order list/detail and payment restart (docs/02 §6-8)."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.forms import AddressForm
from apps.accounts.models import Address
from apps.accounts.services import save_new_address
from apps.cart import services as cart_services
from apps.core.decorators import login_required_htmx
from apps.core.http import client_ip
from apps.orders import services
from apps.orders.forms import CheckoutBuyerForm
from apps.orders.models import Order
from apps.orders.shipping import default_method
from apps.payments import gateways
from apps.payments import services as payment_services


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _neshan_context() -> dict:
    return {"neshan_map_key": settings.NESHAN_MAP_KEY, "neshan_service_enabled": bool(settings.NESHAN_SERVICE_KEY)}


def _addresses(user) -> list[Address]:
    queryset = Address.objects.filter(user=user, deleted_at__isnull=True).select_related("province", "city")
    return list(queryset.order_by("-is_default", "id"))


def _default_address_id(addresses: list[Address]) -> int | None:
    return next((a.pk for a in addresses if a.is_default), addresses[0].pk if addresses else None)


def _buyer_form(user, data=None):
    form = CheckoutBuyerForm(data, user=user)
    return form if form.fields else None


def _address_section_context(user, *, selected=None, address_form=None) -> dict:
    addresses = _addresses(user)
    return {
        "addresses": addresses,
        "selected_address_id": selected or _default_address_id(addresses),
        "address_form": address_form,
        "form_action": reverse("orders:address_new"),
        "form_target": "#checkout-addresses",
        **_neshan_context(),
    }


def _checkout_page(request, *, buyer_form, errors=(), selected_address_id=None, selected_gateway=""):
    lines, notices = cart_services.normalize(cart_services.get_cart(request.user))
    if not lines:
        return redirect("cart:detail")
    summary = cart_services.summarize(lines)
    method = default_method()
    options = gateways.available(summary.items_total)
    context = {
        "lines": lines,
        "notices": notices,
        "summary": summary,
        "method": method,
        "fingerprint": cart_services.fingerprint(lines),
        "buyer_form": buyer_form,
        "errors": list(errors),
        "gateways": options,
        "selected_gateway": selected_gateway or (options[0].code if options else ""),
        "too_heavy": bool(method and method.max_weight_g and summary.weight_g > method.max_weight_g),
        **_address_section_context(request.user, selected=selected_address_id),
    }
    return render(request, "pages/checkout.html", context)


@login_required_htmx
@require_GET
def checkout_view(request):
    return _checkout_page(request, buyer_form=_buyer_form(request.user))


def _pay(request, order: Order, gateway_code: str):
    try:
        url = payment_services.start(order, gateway_code, ip=client_ip(request))
    except payment_services.PaymentStartError:
        messages.error(request, "اتصال به درگاه برقرار نشد. از صفحه‌ی سفارش دوباره پرداخت کنید")
        return redirect("orders:detail", number=order.number)
    return redirect(url)


@login_required_htmx
@require_POST
def place_view(request):
    user = request.user
    method = default_method()
    buyer_form = _buyer_form(user, request.POST)
    address = (
        Address.objects.filter(pk=_int(request.POST.get("address_id")), user=user, deleted_at__isnull=True)
        .select_related("province", "city")
        .first()
    )
    lines, _ = cart_services.normalize(cart_services.get_cart(user))
    allowed = {g.code for g in gateways.available(cart_services.summarize(lines).items_total)}
    gateway_code = request.POST.get("gateway", "")

    errors = []
    if method is None:
        errors.append("ارسال در حال حاضر ممکن نیست")
    if address is None:
        errors.append("آدرس تحویل را انتخاب کنید")
    if gateway_code not in allowed:
        errors.append("روش پرداخت را انتخاب کنید")
    if buyer_form is not None and not buyer_form.is_valid():
        errors.append("اطلاعات خریدار را کامل و درست وارد کنید")

    if not errors:
        try:
            order = services.place_order(
                user=user,
                address=address,
                method=method,
                buyer_form=buyer_form,
                seen_fingerprint=request.POST.get("fingerprint", ""),
            )
        except services.CheckoutError as exc:
            errors.append(str(exc))
            user.refresh_from_db()  # the rolled-back profile save must not leak into the re-rendered page
        else:
            return _pay(request, order, gateway_code)

    return _checkout_page(
        request,
        buyer_form=buyer_form,
        errors=errors,
        selected_address_id=address.pk if address else None,
        selected_gateway=gateway_code,
    )


@login_required_htmx
@require_http_methods(["GET", "POST"])
def address_new_view(request):
    """Inline address creation inside checkout: the form on GET, the refreshed address section on POST."""
    if request.method == "POST":
        form = AddressForm(request.POST, user=request.user)
        if form.is_valid():
            address = save_new_address(request.user, form)
            return render(
                request,
                "partials/_checkout_addresses.html",
                _address_section_context(request.user, selected=address.pk),
            )
        return render(
            request, "partials/_checkout_addresses.html", _address_section_context(request.user, address_form=form)
        )
    context = {
        "form": AddressForm(user=request.user),
        "form_action": reverse("orders:address_new"),
        "form_target": "#checkout-addresses",
        **_neshan_context(),
    }
    return render(request, "partials/_address_form.html", context)


# --- orders ----------------------------------------------------------------


def _order_context(request, number: str, **extra) -> dict:
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number, user=request.user)
    return {"order": order, "gateways": gateways.available(order.payable) if order.can_pay_now else [], **extra}


@login_required_htmx
@require_GET
def order_list_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")[:50]
    return render(request, "pages/orders.html", {"orders": orders})


@login_required_htmx
@require_GET
def order_detail_view(request, number):
    return render(request, "pages/order_detail.html", _order_context(request, number))


@login_required_htmx
@require_GET
def order_result_view(request, number):
    return render(request, "pages/order_detail.html", _order_context(request, number, result=True))


@login_required_htmx
@require_POST
def pay_view(request, number):
    order = get_object_or_404(Order, number=number, user=request.user)
    allowed = [g.code for g in gateways.available(order.payable)]
    code = request.POST.get("gateway")
    code = code if code in allowed else (allowed[0] if allowed else "")
    if not order.can_pay_now or not code:
        messages.error(request, "این سفارش قابل پرداخت نیست")
        return redirect("orders:detail", number=number)
    return _pay(request, order, code)
```

**`apps/orders/urls.py`** (`app_name = "orders"`)

```python
from django.urls import path

from apps.orders import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout_view, name="checkout"),
    path("checkout/place/", views.place_view, name="place"),
    path("checkout/address/new/", views.address_new_view, name="address_new"),
    path("account/orders/", views.order_list_view, name="list"),
    path("account/orders/<str:number>/", views.order_detail_view, name="detail"),
    path("account/orders/<str:number>/pay/", views.pay_view, name="pay"),
    path("orders/<str:number>/result/", views.order_result_view, name="result"),
]
```

**`apps/orders/admin.py`** (فقط‌خواندنی؛ گردش‌کار در P6)

```python
from django.contrib import admin

from apps.orders.models import Order, OrderItem, OrderStatusLog, ShippingMethod
from apps.payments.models import Payment


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "payment_mode", "has_tracking", "max_weight_g", "is_active", "sort")
    list_editable = ("is_active", "sort")


class _ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


class OrderItemInline(_ReadOnlyInline):
    model = OrderItem
    fields = ("product_title", "variant_title", "sku", "unit_price", "qty")


class PaymentInline(_ReadOnlyInline):
    model = Payment
    fields = ("gateway_code", "amount", "status", "ref_id", "created_at")


class OrderStatusLogInline(_ReadOnlyInline):
    model = OrderStatusLog
    fields = ("from_status", "to_status", "note", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "payable", "created_at")
    list_filter = ("status",)
    search_fields = ("number", "buyer_mobile", "recipient_mobile")
    inlines = (OrderItemInline, PaymentInline, OrderStatusLogInline)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
```

**`apps/orders/management/commands/expire_orders.py`** (پوشه‌های `management/` و `commands/` با `__init__.py`)

```python
"""Expire unpaid orders past their reservation and return the stock. Safe to run repeatedly."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.orders import services
from apps.orders.models import Order
from apps.payments import services as payment_services


class Command(BaseCommand):
    help = "Expire unpaid orders whose reservation ended (every 5 minutes; cron/timer lands in P6)."

    def handle(self, *args, **options):
        payment_services.requeue_stale_verifying()  # a crashed callback must not pin a reservation forever
        due = list(
            Order.objects.filter(status=Order.PENDING, reserved_until__lt=timezone.now()).values_list("pk", flat=True)
        )
        expired = sum(1 for pk in due if services.expire_order(pk))
        self.stdout.write(self.style.SUCCESS(f"{expired} order(s) expired."))
```

**`Makefile`**: `expire` را به `.PHONY` اضافه کن و این هدف را بگذار: `expire:` ← `uv run python manage.py expire_orders`.

**مهاجرت‌ها:** `uv run python manage.py makemigrations cart orders payments` و بعد `orders/migrations/0002_seed_shipping_method.py` (کد بالا در گام ۴). در انتهای فاز `makemigrations --check --dry-run` باید بدون تغییر باشد.

---

### گام ۵ — اپ `payments`

ساختار: `apps/payments/{__init__,apps,models,gateways,services,views,urls,admin}.py` و `tests/`.

**`models.py`**

```python
from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class PaymentGateway(TimeStampedModel):
    code = models.SlugField(max_length=32, unique=True, verbose_name="کد")
    title = models.CharField(max_length=120, verbose_name="عنوان")
    logo = models.ImageField(upload_to="gateways/", blank=True, verbose_name="لوگو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    min_amount = models.BigIntegerField(default=0, verbose_name="حداقل مبلغ (تومان)")
    max_amount = models.BigIntegerField(null=True, blank=True, verbose_name="حداکثر مبلغ (تومان)")

    class Meta:
        verbose_name = "درگاه پرداخت"
        verbose_name_plural = "درگاه‌های پرداخت"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.title

    def accepts(self, amount: int) -> bool:
        return amount >= self.min_amount and (self.max_amount is None or amount <= self.max_amount)


class Payment(TimeStampedModel):
    INITIATED = "initiated"
    REDIRECTED = "redirected"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (INITIATED, "ایجادشده"),
        (REDIRECTED, "ارجاع به درگاه"),
        (VERIFYING, "در حال تایید"),
        (VERIFIED, "تاییدشده"),
        (FAILED, "ناموفق"),
        (CANCELLED, "لغوشده"),
    ]
    # A callback that claimed VERIFYING and then died is put back to REDIRECTED after this long.
    VERIFY_STALE = timedelta(minutes=2)

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments", verbose_name="سفارش")
    gateway_code = models.CharField(max_length=32, verbose_name="درگاه")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    authority = models.CharField(max_length=64, blank=True, verbose_name="شناسه مرجع")
    ref_id = models.CharField(max_length=32, blank=True, verbose_name="شماره تراکنش")
    card_pan_masked = models.CharField(max_length=32, blank=True, verbose_name="کارت")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=INITIATED, verbose_name="وضعیت")
    request_payload = models.JSONField(default=dict, blank=True)  # never secrets
    verify_payload = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["gateway_code", "authority"],
                condition=~Q(authority=""),
                name="uniq_payment_gateway_authority",
            )
        ]
        indexes = [models.Index(fields=["order", "status"], name="payment_order_status_idx")]
```

**`gateways.py`**

```python
"""Gateway adapters (docs/02 §7). Money is Toman everywhere except inside an adapter's wire format (D14)."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.urls import reverse

from apps.payments.models import PaymentGateway


class GatewayError(Exception):
    """The gateway refused the request or could not be reached."""


@dataclass(frozen=True)
class StartResult:
    authority: str
    redirect_url: str
    payload: dict


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    ref_id: str = ""
    card_pan: str = ""
    payload: dict = field(default_factory=dict)
    retryable: bool = False  # network trouble: decide nothing, let the customer retry


class BaseGateway:
    code = ""
    dev_only = False

    def request(
        self, *, amount: int, callback_url: str, description: str, mobile: str, order_number: str
    ) -> StartResult:
        raise NotImplementedError

    def verify(self, *, authority: str, amount: int) -> VerifyResult:
        raise NotImplementedError

    def parse_callback(self, params) -> tuple[str, bool]:
        """(authority, customer_reports_success)"""
        return params.get("Authority", ""), params.get("Status") == "OK"


class ZarinpalGateway(BaseGateway):
    code = "zarinpal"
    # Synthetic: the sandbox accepts any UUID (docs/vendors/zarinpal §6). Never used when ZARINPAL_SANDBOX is false.
    SANDBOX_MERCHANT_ID = "00000000-0000-4000-8000-000000000000"

    @property
    def _host(self) -> str:
        return "sandbox.zarinpal.com" if settings.ZARINPAL_SANDBOX else "payment.zarinpal.com"

    def _merchant_id(self) -> str:
        if settings.ZARINPAL_MERCHANT_ID:
            return settings.ZARINPAL_MERCHANT_ID
        if settings.ZARINPAL_SANDBOX:
            return self.SANDBOX_MERCHANT_ID
        raise GatewayError("ZARINPAL_MERCHANT_ID is not configured")

    def _post(self, path: str, body: dict) -> dict:
        http_request = Request(
            f"https://{self._host}/pg/v4/payment/{path}.json",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(http_request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except HTTPError as exc:  # errors still carry a JSON body with the gateway code
            try:
                return json.loads(exc.read().decode("utf-8") or "{}")
            except ValueError:
                raise GatewayError(f"HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise GatewayError(exc.__class__.__name__) from exc

    @staticmethod
    def _code(body: dict) -> int | None:
        for part in (body.get("data"), body.get("errors")):
            if isinstance(part, dict) and "code" in part:
                try:
                    return int(part["code"])
                except (TypeError, ValueError):
                    return None
        return None

    def request(self, *, amount, callback_url, description, mobile, order_number) -> StartResult:
        body = self._post(
            "request",
            {
                "merchant_id": self._merchant_id(),
                "amount": amount * 10,  # Toman -> Rial, only here
                "currency": "IRR",
                "description": description,
                "callback_url": callback_url,
                "metadata": {"mobile": mobile, "order_id": order_number},
            },
        )
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        authority = str(data.get("authority") or "")
        code = self._code(body)
        if code != 100 or not authority:
            raise GatewayError(f"request code={code}")
        # [VERIFY] StartPay URL is from memory; the vendor guide only says "put the authority at the end of the gateway URL".
        return StartResult(authority, f"https://{self._host}/pg/StartPay/{authority}", {"code": code})

    def verify(self, *, authority, amount) -> VerifyResult:
        try:
            body = self._post(
                "verify", {"merchant_id": self._merchant_id(), "amount": amount * 10, "authority": authority}
            )
        except GatewayError:
            return VerifyResult(False, retryable=True)
        code = self._code(body)
        if code is None:
            return VerifyResult(False, retryable=True)
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        if code in (100, 101):  # 101 = already verified (a repeated callback): still a success
            return VerifyResult(
                True,
                ref_id=str(data.get("ref_id") or ""),
                card_pan=str(data.get("card_pan") or ""),
                payload={"code": code, "fee": data.get("fee")},
            )
        return VerifyResult(False, payload={"code": code})


class FakeGateway(BaseGateway):
    """DEBUG only: pay or cancel on a local page, no network (CLAUDE.md §2, D26)."""

    code = "fake"
    dev_only = True

    def request(self, *, amount, callback_url, description, mobile, order_number) -> StartResult:
        authority = f"FAKE{secrets.token_hex(12).upper()}"
        return StartResult(authority, reverse("payments:fake_bank", args=[authority]), {})

    def verify(self, *, authority, amount) -> VerifyResult:
        return VerifyResult(True, ref_id=str(secrets.randbelow(10**9)), card_pan="603799******1234")


_REGISTRY = {cls.code: cls() for cls in (ZarinpalGateway, FakeGateway)}


def adapter_for(code: str) -> BaseGateway:
    adapter = _REGISTRY[code]  # KeyError for unknown codes
    if adapter.dev_only and not settings.DEBUG:
        raise KeyError(code)
    return adapter


def available(amount: int | None = None) -> list[PaymentGateway]:
    rows = []
    for row in PaymentGateway.objects.filter(is_active=True):
        adapter = _REGISTRY.get(row.code)
        if adapter is None or (adapter.dev_only and not settings.DEBUG):
            continue
        if amount is None or row.accepts(amount):
            rows.append(row)
    return rows
```

**`services.py`** (قلب پول؛ همه‌ی تماس‌های شبکه بیرون از تراکنش)

```python
"""Payment lifecycle: start, callback, finalize (docs/02 §7). No network call ever runs inside a transaction."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.cart import services as cart_services
from apps.cart.models import CartItem
from apps.catalog import stock
from apps.notifications import sms
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments import gateways
from apps.payments.models import Payment

logger = logging.getLogger(__name__)


class PaymentStartError(Exception):
    """The gateway could not be reached or refused the request."""


@dataclass(frozen=True)
class Outcome:
    # paid | cancelled | failed | processing | retry | paid_no_stock | duplicate | unknown
    state: str
    order: Order | None = None


def _move(payment_id: int, expected: Iterable[str], **fields) -> bool:
    """Conditional status change: True only for the caller that actually moved it."""
    return bool(
        Payment.objects.filter(pk=payment_id, status__in=list(expected)).update(updated_at=timezone.now(), **fields)
    )


def requeue_stale_verifying() -> int:
    cutoff = timezone.now() - Payment.VERIFY_STALE
    return Payment.objects.filter(status=Payment.VERIFYING, updated_at__lt=cutoff).update(
        status=Payment.REDIRECTED, updated_at=timezone.now()
    )


def start(order: Order, gateway_code: str, *, ip: str | None = None) -> str:
    """Record the Payment first, then ask the gateway (outside any transaction). Returns the URL to redirect to."""
    if not order.can_pay_now:
        raise PaymentStartError("order is not payable")
    try:
        adapter = gateways.adapter_for(gateway_code)
    except KeyError as exc:
        raise PaymentStartError(f"unknown gateway {gateway_code!r}") from exc

    payment = Payment.objects.create(order=order, gateway_code=gateway_code, amount=order.payable, ip=ip)
    callback = f"{settings.SITE_URL}{reverse('payments:callback', args=[gateway_code])}"
    try:
        result = adapter.request(
            amount=payment.amount,
            callback_url=callback,
            description=f"سفارش {order.number}",
            mobile=order.buyer_mobile,
            order_number=order.number,
        )
    except gateways.GatewayError as exc:
        _move(payment.pk, [Payment.INITIATED], status=Payment.FAILED, request_payload={"error": str(exc)})
        logger.warning("Payment %s could not start: %s", payment.pk, exc)
        raise PaymentStartError(str(exc)) from exc
    _move(
        payment.pk,
        [Payment.INITIATED],
        status=Payment.REDIRECTED,
        authority=result.authority,
        request_payload=result.payload,
    )
    return result.redirect_url


def handle_callback(gateway_code: str, params) -> Outcome:
    """Idempotent: any number of callbacks for one authority pay the order at most once."""
    adapter = gateways.adapter_for(gateway_code)  # KeyError -> the view answers 404
    authority, reported_ok = adapter.parse_callback(params)
    payment = (
        Payment.objects.select_related("order").filter(gateway_code=gateway_code, authority=authority).first()
        if authority
        else None
    )
    if payment is None:
        return Outcome("unknown")
    order = payment.order
    if payment.status == Payment.VERIFIED:
        return Outcome("paid", order)
    if not reported_ok:
        _move(payment.pk, [Payment.INITIATED, Payment.REDIRECTED], status=Payment.CANCELLED)
        return Outcome("cancelled", order)

    # Claim. CANCELLED is claimable on purpose: our own "superseded" cancel must not lose a payment the customer
    # still completes at the bank.
    if not _move(payment.pk, [Payment.REDIRECTED, Payment.CANCELLED], status=Payment.VERIFYING):
        payment.refresh_from_db()
        state = {Payment.VERIFIED: "paid", Payment.FAILED: "failed"}.get(payment.status, "processing")
        return Outcome(state, order)

    result = adapter.verify(authority=authority, amount=payment.amount)  # network: no transaction is open here
    if result.retryable:
        _move(payment.pk, [Payment.VERIFYING], status=Payment.REDIRECTED)
        return Outcome("retry", order)
    if not result.ok:
        _move(payment.pk, [Payment.VERIFYING], status=Payment.FAILED, verify_payload=result.payload)
        logger.warning("Payment %s was not verified: %s", payment.pk, result.payload)
        return Outcome("failed", order)
    return Outcome(_finalize(payment.pk, result), order)


def _finalize(payment_id: int, result: gateways.VerifyResult) -> str:
    now = timezone.now()
    with transaction.atomic():
        if not _move(
            payment_id,
            [Payment.VERIFYING],
            status=Payment.VERIFIED,
            ref_id=result.ref_id,
            card_pan_masked=result.card_pan,
            verify_payload=result.payload,
            verified_at=now,
        ):
            return "paid"  # a concurrent callback already finished it
        payment = Payment.objects.select_related("order").get(pk=payment_id)
        order = payment.order

        if order.status in (Order.EXPIRED, Order.CANCELLED):
            # Money was taken after the reservation ended: take the stock back, or tell a human.
            if not order_services.reserve_again(order):
                logger.error(
                    "Order %s was paid (payment %s) but its stock is gone: refund needed", order.number, payment.pk
                )
                return "paid_no_stock"
        elif order.status != Order.PENDING:
            logger.error("Order %s is already %s: payment %s must be refunded", order.number, order.status, payment.pk)
            return "duplicate"

        order_services.transition(
            order.pk,
            expected=order.status,
            to=Order.PAID,
            note=f"payment {payment.pk}",
            paid_at=now,
            reserved_until=None,
        )
        items = list(order.items.all())
        per_product: dict[int, int] = {}
        for item in items:
            if item.product_id:
                per_product[item.product_id] = per_product.get(item.product_id, 0) + item.qty
        stock.add_purchases(per_product)
        # Only the purchased variants leave the cart: lines added after checkout started stay.
        CartItem.objects.filter(
            cart__user_id=order.user_id, variant_id__in=[i.variant_id for i in items if i.variant_id]
        ).delete()
        cart_services.bust_count(order.user_id)
        transaction.on_commit(lambda: _notify_paid(order.pk))
    return "paid"


def _notify_paid(order_id: int) -> None:
    order = Order.objects.get(pk=order_id)
    try:
        sms.send_template("order_paid", order.buyer_mobile, {"ORDER": order.number, "AMOUNT": f"{order.payable:,}"})
    except Exception:  # an SMS problem must never touch the order (docs/05 §4)
        logger.exception("order_paid SMS failed for %s", order.number)
```

**`views.py`**

```python
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.payments import gateways, services

OUTCOME_MESSAGES = {
    "paid": (messages.SUCCESS, "پرداخت با موفقیت انجام شد"),
    "cancelled": (messages.ERROR, "پرداخت انجام نشد یا لغو شد. تا پایان مهلت رزرو می‌توانید دوباره پرداخت کنید"),
    "failed": (messages.ERROR, "پرداخت تایید نشد. اگر مبلغی از حساب شما کسر شده، تا چند ساعت بازگردانده می‌شود"),
    "paid_no_stock": (messages.ERROR, "پرداخت انجام شد اما موجودی کالا تمام شده است. با پشتیبانی تماس بگیرید"),
    "duplicate": (messages.ERROR, "این سفارش قبلاً پرداخت شده بود. با پشتیبانی تماس بگیرید"),
}


@require_GET
def callback_view(request, code):
    try:
        gateways.adapter_for(code)
    except KeyError as exc:
        raise Http404 from exc
    outcome = services.handle_callback(code, request.GET)
    if outcome.order is None:
        messages.error(request, "پرداخت پیدا نشد")
        return redirect("orders:list")
    if outcome.state in ("processing", "retry"):
        return render(request, "pages/payments/processing.html", {"retry_url": request.get_full_path()})
    level, text = OUTCOME_MESSAGES[outcome.state]
    messages.add_message(request, level, text)
    return redirect("orders:result", number=outcome.order.number)


@require_GET
def fake_bank_view(request, authority):
    if not settings.DEBUG:
        raise Http404
    return render(
        request,
        "pages/payments/fake_bank.html",
        {"authority": authority, "callback": reverse("payments:callback", args=["fake"])},
    )
```

**`urls.py`** (`app_name = "payments"`)

```python
urlpatterns = [
    path("callback/<slug:code>/", views.callback_view, name="callback"),
    path("fake/<str:authority>/", views.fake_bank_view, name="fake_bank"),
]
```

**`admin.py`**: `PaymentGatewayAdmin` (قابل‌ویرایش: `list_display = ("title","code","is_active","sort","min_amount","max_amount")` و `list_editable = ("is_active","sort")`) و `PaymentAdmin` فقط‌خواندنی (`has_add/change/delete_permission` همه `False`؛ `list_display = ("pk","order","gateway_code","amount","status","ref_id","created_at")`، `list_filter = ("status","gateway_code")`، `search_fields = ("order__number","authority","ref_id")`).

**`payments/migrations/0002_seed_gateways.py`** (بعد از `makemigrations`):

```python
from django.db import migrations


def seed(apps, schema_editor):
    Gateway = apps.get_model("payments", "PaymentGateway")
    # [VERIFY] limits: 100M Toman is code -41 in the vendor guide; the Rial minimum differs between pages (1,000 / 10,000 Rial).
    Gateway.objects.get_or_create(
        code="zarinpal", defaults={"title": "زرین‌پال", "sort": 0, "min_amount": 1000, "max_amount": 100_000_000}
    )
    # Hidden in production by the adapter itself (dev_only); the row only makes it selectable while DEBUG is on.
    Gateway.objects.get_or_create(code="fake", defaults={"title": "درگاه آزمایشی (فقط توسعه)", "sort": 99})


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
```

**`[VERIFY]` پیش از پیاده‌سازی:** آدرس StartPay، رفتار sandbox با مرچنت‌کد دلخواه، شکل پاسخ خطا و حداقل مبلغ را با سرویس MCP مستندات (`https://www.zarinpal.com/docs/mcp`) تطبیق بده. تناقض را در `docs/vendors/zarinpal/` یادداشت و در گزارش بنویس.

---

### گام ۶ — رابط: JS، قالب‌ها، ویرایش قالب‌های موجود

**`static/js/mm/cart.js`**

```javascript
/* MM.cart: guest cart (localStorage) + add / quantity controls (docs/02 §5). Prices never live here: only {v, q}. */
(function (MM) {
  "use strict";
  var KEY = "malmal.cart.v1";
  var MAX_LINES = 30;
  var syncing = false;
  var lastAdd = null;

  function isAuth() { return document.body.getAttribute("data-auth") === "1"; }

  function read() {
    try {
      var data = JSON.parse(window.localStorage.getItem(KEY) || "{}");
      return Array.isArray(data.items) ? data.items.filter(function (i) { return i && i.v > 0 && i.q > 0; }) : [];
    } catch (e) { return []; }
  }
  function write(items) {
    try { window.localStorage.setItem(KEY, JSON.stringify({ items: items, updatedAt: Date.now() })); } catch (e) { /* storage blocked */ }
  }
  function clear() { try { window.localStorage.removeItem(KEY); } catch (e) { /* storage blocked */ } }

  function qtyOf(id) {
    var hit = read().filter(function (i) { return i.v === id; })[0];
    return hit ? hit.q : 0;
  }
  function setLocal(id, qty) {
    var items = read().filter(function (i) { return i.v !== id; });
    if (qty > 0) {
      if (items.length >= MAX_LINES) return false;
      items.push({ v: id, q: qty });
    }
    write(items);
    window.malmalSetCartCount(items.length);
    return true;
  }
  function post(url, values, target) {
    var ctx = { swap: target ? "innerHTML" : "none", values: values };
    if (target) ctx.target = target;
    window.htmx.ajax("POST", url, ctx);
  }

  function flash(btn) {
    var label = btn.querySelector("[data-cart-label]");
    if (!label || btn.dataset.flashing) return;
    var original = label.textContent;
    btn.dataset.flashing = "1";
    label.textContent = "در سبد شما";
    window.setTimeout(function () { label.textContent = original; delete btn.dataset.flashing; }, 1600);
  }

  function onAdd(btn) {
    var panel = document.getElementById("variant-panel");
    if (!panel || !panel.dataset.variantId || btn.disabled) return;
    var id = parseInt(panel.dataset.variantId, 10);
    if (isAuth()) {
      lastAdd = btn;
      post("/cart/add/", { variant_id: id });
      return;
    }
    var max = parseInt(panel.dataset.max || "0", 10);
    var next = qtyOf(id) + 1;
    if (max && next > max) {
      MM.ui.toast("حداکثر " + MM.fmt.faDigits(max) + " عدد در هر سفارش", { level: "warning" });
      return;
    }
    if (!setLocal(id, next)) {
      MM.ui.toast("سبد خرید حداکثر " + MM.fmt.faDigits(MAX_LINES) + " قلم کالا دارد", { level: "error" });
      return;
    }
    flash(btn);
  }

  function renderGuest() {
    post("/cart/render/", { items: JSON.stringify(read()) }, "#cart-content");
  }

  function onSet(btn) {
    var id = parseInt(btn.getAttribute("data-variant"), 10);
    var qty = parseInt(btn.getAttribute("data-qty"), 10);
    if (!(id > 0) || !(qty >= 0)) return;
    btn.disabled = true; /* the server takes an absolute quantity, so a double click is harmless anyway */
    if (isAuth()) {
      post("/cart/set/", { variant_id: id, qty: qty }, "#cart-content");
    } else {
      setLocal(id, qty);
      renderGuest();
    }
  }

  document.addEventListener("click", function (event) {
    var target = event.target.closest ? event.target : null;
    if (!target) return;
    var add = target.closest("[data-cart-add]");
    if (add) { onAdd(add); return; }
    var set = target.closest("[data-cart-set]");
    if (set) onSet(set);
  });

  /* Guest items travel with the request: the cart page render, and the OTP verify form (merge before checkout). */
  document.addEventListener("htmx:configRequest", function (event) {
    var el = event.detail.elt;
    if (!el || !el.hasAttribute) return;
    if (el.hasAttribute("data-cart-items")) event.detail.parameters.items = JSON.stringify(read());
    if (el.hasAttribute("data-guest-cart")) event.detail.parameters.guest_cart = JSON.stringify(read());
  });

  function syncButtons() {
    var panel = document.getElementById("variant-panel");
    if (!panel) return;
    var orderable = panel.getAttribute("data-orderable") === "1";
    document.querySelectorAll("[data-cart-add]").forEach(function (b) { b.disabled = !orderable; });
    var price = panel.getAttribute("data-price");
    if (price) document.querySelectorAll("[data-bar-price]").forEach(function (el) { el.textContent = price; });
  }

  document.addEventListener("htmx:afterSwap", function () {
    syncButtons();
    var state = document.getElementById("cart-state");
    if (state && state.getAttribute("data-guest") === "1") {
      try { write(JSON.parse(state.getAttribute("data-normalized") || "[]")); } catch (e) { /* ignore */ }
    }
  });

  document.addEventListener("cart:changed", function (event) {
    var detail = event.detail || {};
    if (typeof detail.count === "number") window.malmalSetCartCount(detail.count);
    if (syncing) { clear(); syncing = false; }
    if (detail.message) MM.ui.toast(detail.message, { level: detail.ok === false ? "error" : "warning" });
    if (lastAdd && detail.ok !== false) flash(lastAdd);
    lastAdd = null;
  });

  document.addEventListener("auth:login", clear); /* the server merged it during verify */

  function syncGuestCart() {
    var items = read();
    if (!isAuth() || !items.length || syncing) return;
    syncing = true;
    post("/cart/sync/", { items: JSON.stringify(items) });
  }

  MM.cart = { read: read, clear: clear };
  MM.init("cart", function () {
    syncButtons();
    if (isAuth()) syncGuestCart();
    else window.malmalSetCartCount(read().length);
  });
})(window.MM);
```

**`pages/cart.html`**

```html
{% extends "base.html" %}
{% load core_tags %}

{% block title %}سبد خرید — {{ site_settings.store_name }}{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-6 lg:py-8 pb-36 lg:pb-8">
  {% include "partials/_section_heading.html" with title="سبد خرید" %}
  <div id="cart-content" class="mt-6 min-h-64" aria-live="polite"
       {% if guest %}data-cart-items hx-post="{% url 'cart:render' %}" hx-trigger="load" hx-swap="innerHTML"{% endif %}>
    {% if guest %}
      <div class="flex flex-col gap-3">
        <div class="skeleton h-28 w-full"></div>
        <div class="skeleton h-28 w-full"></div>
      </div>
    {% else %}
      {% include "partials/_cart_content.html" %}
    {% endif %}
  </div>
</div>
{% endblock %}
```

**`partials/_cart_continue.html`**

```html
{% url 'orders:checkout' as checkout_url %}{% if summary.has_unavailable %}<button type="button" class="btn btn-primary {{ btn_class }}" disabled>ادامه‌ی خرید</button>{% elif guest %}<a href="{% url 'accounts:login' %}?next={{ checkout_url|urlencode }}" data-auth-open hx-get="{% url 'accounts:otp_modal' %}?next={{ checkout_url|urlencode }}" hx-target="#auth-modal-body" hx-swap="innerHTML" class="btn btn-primary {{ btn_class }}">ادامه‌ی خرید</a>{% else %}<a href="{{ checkout_url }}" class="btn btn-primary {{ btn_class }}">ادامه‌ی خرید</a>{% endif %}
```

**`partials/_cart_content.html`**

```html
{% load core_tags catalog_tags %}
<div id="cart-state" class="hidden" data-guest="{% if guest %}1{% else %}0{% endif %}" data-normalized="{{ normalized }}"></div>

{% for notice in notices %}
  <div role="alert" class="alert text-small mb-3">
    {% icon "info" size=18 class="text-ink-2 shrink-0" %}
    <span>{{ notice }}</span>
  </div>
{% endfor %}

{% if lines %}
<div class="lg:grid lg:grid-cols-[1fr_320px] lg:gap-8 items-start">
  <ul class="flex flex-col gap-3">
    {% for line in lines %}
      {% with variant=line.variant product=line.variant.product %}
      <li class="bg-base-100 border rounded-box p-3 flex gap-3">
        <a href="{{ product.get_absolute_url }}" tabindex="-1" aria-hidden="true"
           class="w-20 h-20 shrink-0 rounded-lg bg-white border overflow-hidden flex items-center justify-center">
          {% if product.main_image %}
            <img src="{{ product.main_image|image_url }}" alt="" width="80" height="80" loading="lazy" class="w-full h-full object-contain p-1{% if not line.available %} opacity-60{% endif %}">
          {% else %}
            {% icon "image" size=18 class="text-ink-3" %}
          {% endif %}
        </a>

        <div class="min-w-0 flex-1 flex flex-col gap-2">
          <div class="flex flex-col">
            <a href="{{ product.get_absolute_url }}" class="text-small font-medium leading-6 line-clamp-2">{{ product.title|fa_text }}</a>
            <span class="text-label text-ink-3">{{ variant.title|fa_text }}</span>
          </div>

          {% if line.available %}
            <div class="flex items-center justify-between gap-3">
              <div class="join border rounded-field">
                <button type="button" class="btn btn-ghost join-item w-10 h-10 min-h-10 px-0" data-cart-set
                        data-variant="{{ variant.pk }}" data-qty="{{ line.qty|add:-1 }}"
                        aria-label="{% if line.qty == 1 %}حذف از سبد{% else %}کم کردن{% endif %}">
                  {% if line.qty == 1 %}{% icon "trash-2" size=18 %}{% else %}{% icon "minus" size=18 %}{% endif %}
                </button>
                <span class="join-item flex items-center justify-center w-10 text-small num">{{ line.qty|fa_digits }}</span>
                <button type="button" class="btn btn-ghost join-item w-10 h-10 min-h-10 px-0" data-cart-set
                        data-variant="{{ variant.pk }}" data-qty="{{ line.qty|add:1 }}"
                        {% if line.qty >= variant.max_orderable %}disabled{% endif %} aria-label="زیاد کردن">
                  {% icon "plus" size=18 %}
                </button>
              </div>
              <div class="flex flex-col items-end leading-5">
                <span class="text-small font-medium whitespace-nowrap">{{ line.total|toman }} <span class="text-ink-2 font-normal">تومان</span></span>
                {% if line.qty > 1 %}<span class="text-label text-ink-3 whitespace-nowrap">هر عدد {{ variant.price|toman }}</span>{% endif %}
              </div>
            </div>
            {% if line.qty >= variant.max_orderable and variant.max_per_order %}
              <span class="text-label text-ink-3">حداکثر {{ variant.max_orderable|fa_digits }} عدد در هر سفارش</span>
            {% endif %}
          {% else %}
            <div class="flex items-center justify-between gap-3">
              <span class="flex items-center gap-1 text-small text-ink-2">
                {% icon "alert-circle" size=18 class="text-ink-3" %}ناموجود
              </span>
              <button type="button" class="btn btn-ghost btn-sm h-10 gap-1" data-cart-set data-variant="{{ variant.pk }}" data-qty="0">
                {% icon "trash-2" size=18 %}<span>حذف</span>
              </button>
            </div>
          {% endif %}
        </div>
      </li>
      {% endwith %}
    {% endfor %}
  </ul>

  <aside class="bg-base-100 border rounded-box p-4 flex flex-col gap-3 mt-4 lg:mt-0 lg:sticky lg:top-32">
    <div class="flex items-center justify-between text-small">
      <span class="text-ink-2">جمع کالاها</span>
      <span class="whitespace-nowrap">{{ summary.items_total|toman }} تومان</span>
    </div>
    <div class="flex items-center justify-between text-small">
      <span class="text-ink-2">ارسال</span>
      <span class="text-ink-2">پس‌کرایه</span>
    </div>
    {% if method.checkout_note %}<p class="text-label text-ink-3 leading-5">{{ method.checkout_note }}</p>{% endif %}
    <div class="flex items-center justify-between border-t pt-3">
      <span class="text-small font-medium">مبلغ قابل پرداخت</span>
      <span class="text-lead font-medium whitespace-nowrap">{{ summary.items_total|toman }} <span class="text-small text-ink-2 font-normal">تومان</span></span>
    </div>
    {% if summary.has_unavailable %}
      <div role="alert" class="alert text-small">
        {% icon "alert-circle" size=18 class="text-ink-2 shrink-0" %}
        <span>برای ادامه، کالای ناموجود را از سبد حذف کنید</span>
      </div>
    {% endif %}
    {% include "partials/_cart_continue.html" with btn_class="w-full h-11 min-h-11 hidden lg:inline-flex" %}
  </aside>
</div>

{# D28: primary action at the start (right in RTL), total at the end; above the dock #}
<div class="lg:hidden fixed bottom-16 inset-x-0 z-20 bg-base-100 border-t px-4 py-3">
  <div class="flex items-center gap-3">
    {% include "partials/_cart_continue.html" with btn_class="flex-1 min-w-0 h-11 min-h-11" %}
    <div class="flex flex-col items-end shrink-0 leading-5">
      <span class="text-lead font-medium whitespace-nowrap tabular-nums">{{ summary.items_total|toman }}</span>
      <span class="text-label text-ink-2">تومان</span>
    </div>
  </div>
</div>
{% else %}
  {% url 'core:home' as home_url %}
  {% include "partials/_empty_state.html" with title="سبد خرید خالی است" description="برای شروع، محصولات را ببینید" action_url=home_url action_label="مشاهده‌ی محصولات" %}
{% endif %}
```

**`partials/_checkout_addresses.html`**

```html
{% load core_tags %}
<div id="checkout-addresses" class="flex flex-col gap-3">
  {% for address in addresses %}
    <label class="flex items-start gap-3 border rounded-field p-3 cursor-pointer">
      <input type="radio" name="address_id" value="{{ address.pk }}" form="checkout-form" class="radio radio-sm mt-1"
             {% if address.pk == selected_address_id %}checked{% endif %}>
      <span class="flex flex-col gap-1 min-w-0">
        <span class="text-small font-medium">{{ address.title|default:address.city.name|fa_text }}
          {% if address.is_default %}<span class="badge badge-sm bg-base-300 border-0 ms-1">پیش‌فرض</span>{% endif %}
        </span>
        <span class="text-small text-ink-2 leading-6">{{ address.province.name }}، {{ address.city.name }}، {{ address.address_text|fa_text }}</span>
        <span class="text-label text-ink-3">
          {{ address.recipient_name|fa_text }} — <span class="num">{{ address.recipient_mobile|fa_digits }}</span>
          — پلاک {{ address.plate|fa_digits }}{% if address.unit %}، واحد {{ address.unit|fa_digits }}{% endif %}
        </span>
      </span>
    </label>
  {% endfor %}

  <div id="address-form-container">
    {% if address_form %}{% include "partials/_address_form.html" with form=address_form %}{% endif %}
  </div>

  <button type="button" data-address-add
          class="btn bg-base-100 border h-11 min-h-11 self-start{% if address_form %} hidden{% endif %}"
          hx-get="{% url 'orders:address_new' %}" hx-target="#address-form-container" hx-swap="innerHTML"
          hx-indicator="#address-indicator" hx-disabled-elt="this">
    {% icon "plus" size=18 %}
    <span>{% if addresses %}آدرس تازه{% else %}افزودن آدرس{% endif %}</span>
    <span id="address-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </button>
</div>
```

**`pages/checkout.html`**

```html
{% extends "base.html" %}
{% load static core_tags %}

{% block title %}ثبت سفارش — {{ site_settings.store_name }}{% endblock %}

{% block extra_head %}
  {% if neshan_map_key %}<link rel="stylesheet" href="https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.css">{% endif %}
{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-6 lg:py-8 pb-36 lg:pb-8">
  {% include "partials/_section_heading.html" with title="ثبت سفارش" %}

  {# Fields live outside this form (the address form is a nested HTMX form), tied to it with form="checkout-form". #}
  <form id="checkout-form" method="post" action="{% url 'orders:place' %}" novalidate>
    {% csrf_token %}
    <input type="hidden" name="fingerprint" value="{{ fingerprint }}">
  </form>

  <div class="mt-4 flex flex-col gap-2">
    {% for notice in notices %}
      <div role="alert" class="alert text-small">{% icon "info" size=18 class="text-ink-2 shrink-0" %}<span>{{ notice }}</span></div>
    {% endfor %}
    {% for error in errors %}
      <div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ error }}</span></div>
    {% endfor %}
  </div>

  <div class="mt-6 lg:grid lg:grid-cols-[1fr_340px] lg:gap-8 items-start">
    <div class="flex flex-col gap-4">

      {% if buyer_form %}
      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" aria-labelledby="buyer-title">
        <div>
          <h2 id="buyer-title" class="text-lead font-medium">مشخصات خریدار</h2>
          <p class="text-small text-ink-2 mt-1">فقط موارد تکمیل‌نشده‌ی پروفایل پرسیده می‌شود</p>
        </div>
        <div class="grid sm:grid-cols-2 gap-4">
          {% for field in buyer_form.visible_fields %}
            {% if field.name != "national_code_confirm" %}
            <fieldset class="fieldset{% if field.name == 'national_code' %} sm:col-span-2{% endif %}">
              <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
              {{ field }}
              {% for error in field.errors %}
                <p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ error }}</span></p>
              {% endfor %}
              {% if field.name == "national_code" %}
                <div role="alert" class="alert text-small mt-2 items-start">
                  {% icon "info" size=18 class="text-ink-2 shrink-0 mt-0.5" %}
                  <div class="flex flex-col gap-2">
                    <span>کد ملی بعد از ثبت قابل تغییر نیست. از درستی آن مطمئن شوید</span>
                    <label class="flex items-start gap-2 cursor-pointer">
                      {{ buyer_form.national_code_confirm }}
                      <span class="text-label text-ink-2 leading-5">{{ buyer_form.national_code_confirm.label }}</span>
                    </label>
                  </div>
                </div>
              {% endif %}
            </fieldset>
            {% endif %}
          {% endfor %}
        </div>
      </section>
      {% endif %}

      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3" aria-labelledby="address-title">
        <h2 id="address-title" class="text-lead font-medium">آدرس و گیرنده</h2>
        <p class="text-small text-ink-2">گیرنده همان نامی است که در آدرس ثبت شده؛ برای گیرنده‌ی دیگر یک آدرس جدید بسازید</p>
        {% include "partials/_checkout_addresses.html" %}
      </section>

      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3" aria-labelledby="shipping-title">
        <h2 id="shipping-title" class="text-lead font-medium">روش ارسال</h2>
        {% if method %}
          <div class="flex items-start gap-3">
            {% icon "truck" size=20 class="text-ink-2 shrink-0 mt-0.5" %}
            <div>
              <p class="text-small font-medium">{{ method.title }}</p>
              <p class="text-label text-ink-3 mt-1 leading-5">{{ method.checkout_note }}</p>
            </div>
          </div>
        {% else %}
          <div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>ارسال در حال حاضر ممکن نیست</span></div>
        {% endif %}
      </section>

      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3" aria-labelledby="payment-title">
        <h2 id="payment-title" class="text-lead font-medium">روش پرداخت</h2>
        {% for gateway in gateways %}
          <label class="flex items-center gap-3 border rounded-field p-3 cursor-pointer min-h-12">
            <input type="radio" name="gateway" value="{{ gateway.code }}" form="checkout-form" class="radio radio-sm"
                   {% if gateway.code == selected_gateway %}checked{% endif %}>
            {% if gateway.logo %}
              <img src="{{ gateway.logo.url }}" alt="" width="32" height="32" class="h-8 w-auto">
            {% else %}
              {% icon "credit-card" size=20 class="text-ink-2" %}
            {% endif %}
            <span class="text-small">{{ gateway.title }}</span>
          </label>
        {% empty %}
          <div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>پرداخت برای این مبلغ در حال حاضر ممکن نیست</span></div>
        {% endfor %}
      </section>
    </div>

    <aside class="bg-base-100 border rounded-box p-4 flex flex-col gap-3 mt-4 lg:mt-0 lg:sticky lg:top-32">
      <h2 class="text-lead font-medium">خلاصه‌ی سفارش</h2>
      <ul class="flex flex-col gap-2 border-b pb-3">
        {% for line in lines %}
          <li class="flex items-start justify-between gap-2 text-small">
            <span class="min-w-0 truncate">{{ line.variant.product.title|fa_text }} <span class="text-ink-3">× {{ line.qty|fa_digits }}</span></span>
            <span class="whitespace-nowrap shrink-0">{{ line.total|toman }}</span>
          </li>
        {% endfor %}
      </ul>
      <div class="flex items-center justify-between text-small">
        <span class="text-ink-2">جمع کالاها</span><span class="whitespace-nowrap">{{ summary.items_total|toman }} تومان</span>
      </div>
      <div class="flex items-center justify-between text-small">
        <span class="text-ink-2">ارسال</span><span class="text-ink-2">پس‌کرایه</span>
      </div>
      <div class="flex items-center justify-between border-t pt-3">
        <span class="text-small font-medium">مبلغ قابل پرداخت</span>
        <span class="text-lead font-medium whitespace-nowrap">{{ summary.items_total|toman }} <span class="text-small text-ink-2 font-normal">تومان</span></span>
      </div>
      {% if too_heavy %}
        <div role="alert" class="alert alert-error text-small">
          {% icon "alert-circle" size=18 class="shrink-0" %}
          <span>برای ارسال این سفارش لطفاً با پشتیبانی تماس بگیرید{% if site_settings.phone %}: <span class="num">{{ site_settings.phone|fa_digits }}</span>{% endif %}</span>
        </div>
      {% endif %}
      <button type="submit" form="checkout-form" class="btn btn-primary w-full h-11 min-h-11 hidden lg:inline-flex"
              {% if not gateways or too_heavy or not method %}disabled{% endif %}>پرداخت</button>
      <a href="{% url 'cart:detail' %}" class="btn btn-ghost h-10 text-ink-2 hidden lg:inline-flex">بازگشت به سبد</a>
    </aside>
  </div>
</div>

{# D28 #}
<div class="lg:hidden fixed bottom-16 inset-x-0 z-20 bg-base-100 border-t px-4 py-3">
  <div class="flex items-center gap-3">
    <button type="submit" form="checkout-form" class="btn btn-primary flex-1 min-w-0 h-11 min-h-11"
            {% if not gateways or too_heavy or not method %}disabled{% endif %}>پرداخت</button>
    <div class="flex flex-col items-end shrink-0 leading-5">
      <span class="text-lead font-medium whitespace-nowrap tabular-nums">{{ summary.items_total|toman }}</span>
      <span class="text-label text-ink-2">تومان</span>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
  <script src="{% static 'js/mm/addresses.js' %}" defer></script>
  {% if neshan_map_key %}
    <script src="https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js" defer></script>
    <script src="{% static 'js/mm/neshan.js' %}" defer></script>
  {% endif %}
{% endblock %}
```

**`partials/_order_summary.html`**

```html
{% load core_tags jalali_tags %}
<section class="bg-base-100 border rounded-box p-4 flex flex-col gap-4">
  <div class="flex flex-wrap items-center justify-between gap-2">
    <span class="flex items-center gap-2 text-small">
      <span class="status {{ order.status_dot }}"></span>{{ order.get_status_display }}
    </span>
    <span class="text-label text-ink-3">{{ order.created_at|to_jalali }}</span>
  </div>

  <ul class="flex flex-col divide-y">
    {% for item in order.items.all %}
      <li class="flex items-center gap-3 py-3 first:pt-0">
        <span class="w-14 h-14 shrink-0 rounded-lg bg-white border overflow-hidden flex items-center justify-center">
          {% if item.image_url %}<img src="{{ item.image_url }}" alt="" width="56" height="56" loading="lazy" class="w-full h-full object-contain p-1">{% else %}{% icon "image" size=18 class="text-ink-3" %}{% endif %}
        </span>
        <span class="min-w-0 flex-1 flex flex-col">
          <span class="text-small leading-6 line-clamp-2">{{ item.product_title|fa_text }}</span>
          <span class="text-label text-ink-3">{{ item.variant_title|fa_text }} — {{ item.qty|fa_digits }} عدد</span>
        </span>
        <span class="text-small whitespace-nowrap shrink-0">{{ item.line_total|toman }}</span>
      </li>
    {% endfor %}
  </ul>

  <div class="flex flex-col gap-2 border-t pt-3 text-small">
    <div class="flex items-center justify-between"><span class="text-ink-2">جمع کالاها</span><span class="whitespace-nowrap">{{ order.items_total|toman }} تومان</span></div>
    <div class="flex items-center justify-between"><span class="text-ink-2">ارسال</span><span class="text-ink-2">{% if order.shipping_payment_mode == "collect" %}پس‌کرایه{% else %}{{ order.shipping_cost|toman }} تومان{% endif %}</span></div>
    <div class="flex items-center justify-between"><span class="font-medium">مبلغ پرداختی</span><span class="text-lead font-medium whitespace-nowrap">{{ order.payable|toman }} تومان</span></div>
  </div>

  <div class="flex flex-col gap-1 border-t pt-3 text-small">
    <span class="font-medium">تحویل‌گیرنده</span>
    <span class="text-ink-2">{{ order.recipient_name|fa_text }} — <span class="num">{{ order.recipient_mobile|fa_digits }}</span></span>
    <span class="text-ink-2 leading-6">{{ order.province_name }}، {{ order.city_name }}، {{ order.address_text|fa_text }}</span>
    <span class="text-label text-ink-3">پلاک {{ order.plate|fa_digits }}{% if order.unit %}، واحد {{ order.unit|fa_digits }}{% endif %} — کدپستی <span class="num">{{ order.postal_code|fa_digits }}</span></span>
  </div>

  <div class="flex flex-col gap-1 border-t pt-3 text-small">
    <span class="font-medium">{{ order.shipping_method_title }}</span>
    {% if order.shipping_payment_mode == "collect" %}<span class="text-label text-ink-3 leading-5">کرایه‌ی ارسال هنگام تحویل بار به پیک پرداخت می‌شود و جزو مبلغ این پرداخت نیست</span>{% endif %}
    {% if order.tracking_code %}<span class="text-ink-2">کد رهگیری: <span class="latin">{{ order.tracking_code }}</span></span>{% endif %}
  </div>
</section>
```

**`pages/order_detail.html`**

```html
{% extends "base.html" %}
{% load core_tags %}

{% block title %}سفارش {{ order.number }} — {{ site_settings.store_name }}{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto px-4 py-6 lg:py-8 pb-36 lg:pb-8">
  <h1 class="text-title font-medium">
    {% if result %}نتیجه‌ی پرداخت{% else %}سفارش{% endif %} <span class="latin text-ink-2">{{ order.number }}</span>
  </h1>
  {% include "partials/_account_nav.html" with active="orders" %}

  {% if result and order.status == "pending_payment" and order.can_pay_now %}
    <div role="alert" class="alert text-small mt-4">
      {% icon "info" size=18 class="text-ink-2 shrink-0" %}
      <span>پرداخت کامل نشد. رزرو کالاها تا ساعت <span class="num">{% load jalali_tags %}{{ order.reserved_until|to_jalali:"%H:%M" }}</span> نگه داشته می‌شود</span>
    </div>
  {% endif %}

  <div class="mt-4">{% include "partials/_order_summary.html" %}</div>

  {% if order.can_pay_now and gateways %}
    <form id="pay-form" method="post" action="{% url 'orders:pay' order.number %}" class="mt-4 bg-base-100 border rounded-box p-4 flex flex-col gap-3">
      {% csrf_token %}
      {% if gateways|length > 1 %}
        {% for gateway in gateways %}
          <label class="flex items-center gap-3 border rounded-field p-3 cursor-pointer min-h-12">
            <input type="radio" name="gateway" value="{{ gateway.code }}" class="radio radio-sm" {% if forloop.first %}checked{% endif %}>
            <span class="text-small">{{ gateway.title }}</span>
          </label>
        {% endfor %}
      {% else %}
        <input type="hidden" name="gateway" value="{{ gateways.0.code }}">
      {% endif %}
      <button type="submit" class="btn btn-primary h-11 min-h-11 hidden lg:inline-flex lg:self-start">پرداخت</button>
    </form>

    <div class="lg:hidden fixed bottom-16 inset-x-0 z-20 bg-base-100 border-t px-4 py-3">
      <div class="flex items-center gap-3">
        <button type="submit" form="pay-form" class="btn btn-primary flex-1 min-w-0 h-11 min-h-11">پرداخت</button>
        <div class="flex flex-col items-end shrink-0 leading-5">
          <span class="text-lead font-medium whitespace-nowrap tabular-nums">{{ order.payable|toman }}</span>
          <span class="text-label text-ink-2">تومان</span>
        </div>
      </div>
    </div>
  {% endif %}
</div>
{% endblock %}
```

**`pages/orders.html`**

```html
{% extends "base.html" %}
{% load core_tags jalali_tags %}

{% block title %}سفارش‌های من — {{ site_settings.store_name }}{% endblock %}

{% block content %}
<div class="max-w-3xl mx-auto px-4 py-6 lg:py-8">
  <h1 class="text-title font-medium">حساب کاربری</h1>
  {% include "partials/_account_nav.html" with active="orders" %}
  <ul class="mt-6 flex flex-col gap-3">
    {% for order in orders %}
      <li>
        <a href="{% url 'orders:detail' order.number %}" class="block bg-base-100 border rounded-box p-4 hover:bg-base-300 transition-colors">
          <div class="flex items-center justify-between gap-2">
            <span class="latin text-small font-medium">{{ order.number }}</span>
            <span class="flex items-center gap-2 text-small"><span class="status {{ order.status_dot }}"></span>{{ order.get_status_display }}</span>
          </div>
          <div class="flex items-center justify-between gap-2 mt-2 text-label text-ink-3">
            <span>{{ order.created_at|to_jalali }} — {{ order.items.all|length|fa_digits }} قلم</span>
            <span class="text-small text-base-content whitespace-nowrap">{{ order.payable|toman }} تومان</span>
          </div>
        </a>
      </li>
    {% empty %}
      <li>{% include "partials/_empty_state.html" with title="هنوز سفارشی ثبت نکرده‌اید" description="سفارش‌های شما بعد از ثبت اینجا دیده می‌شود" %}</li>
    {% endfor %}
  </ul>
</div>
{% endblock %}
```

**`pages/payments/fake_bank.html`** و **`pages/payments/processing.html`**

```html
{# fake_bank.html #}
{% extends "base.html" %}
{% block title %}درگاه آزمایشی{% endblock %}
{% block content %}
<div class="max-w-md mx-auto px-4 py-8">
  <div class="bg-base-100 border rounded-box p-5 flex flex-col gap-4">
    <h1 class="text-title font-medium">درگاه آزمایشی</h1>
    <p class="text-small text-ink-2">فقط در حالت توسعه دیده می‌شود. نتیجه‌ی پرداخت را انتخاب کنید</p>
    <div class="flex items-center gap-2 border-t pt-4">
      <a href="{{ callback }}?Authority={{ authority }}&amp;Status=OK" class="btn btn-primary flex-1 h-11">پرداخت موفق</a>
      <a href="{{ callback }}?Authority={{ authority }}&amp;Status=NOK" class="btn btn-ghost h-11 text-ink-2">انصراف</a>
    </div>
  </div>
</div>
{% endblock %}
```

```html
{# processing.html #}
{% extends "base.html" %}
{% load core_tags %}
{% block title %}بررسی پرداخت — {{ site_settings.store_name }}{% endblock %}
{% block content %}
<div class="max-w-md mx-auto px-4 py-12 text-center">
  <div class="bg-base-100 border rounded-box p-6 flex flex-col items-center gap-3">
    {% icon "info" size=40 class="text-ink-3" %}
    <h1 class="text-title font-medium">پرداخت در حال بررسی است</h1>
    <p class="text-small text-ink-2">چند لحظه بعد دوباره بررسی کنید. مبلغ فقط یک بار از شما دریافت می‌شود</p>
    <a href="{{ retry_url }}" class="btn btn-primary h-11 mt-2">بررسی دوباره</a>
    <a href="{% url 'orders:list' %}" class="btn btn-ghost h-10 text-ink-2">سفارش‌های من</a>
  </div>
</div>
{% endblock %}
```

### ویرایش قالب‌های موجود

**`templates/partials/_address_form.html`**: سه مقدار پارامتری شود (رفتار حساب کاربری عوض نمی‌شود).

```html
{# replace the action, hx-post and hx-target lines of the <form> with: #}
      action="{% if form_action %}{{ form_action }}{% elif form.instance.pk %}{% url 'accounts:address_edit' form.instance.pk %}{% else %}{% url 'accounts:address_create' %}{% endif %}"
      hx-post="{% if form_action %}{{ form_action }}{% elif form.instance.pk %}{% url 'accounts:address_edit' form.instance.pk %}{% else %}{% url 'accounts:address_create' %}{% endif %}"
      hx-target="{{ form_target|default:'#addresses-section' }}"
```

**`templates/partials/_variant_panel.html`**

```html
{# root element #}
<div id="variant-panel" class="flex flex-col gap-4"
     data-variant-id="{{ active_variant.pk|default:'' }}"
     data-max="{{ active_variant.max_orderable|default:0 }}"
     data-orderable="{% if active_variant and active_variant.max_orderable > 0 %}1{% else %}0{% endif %}"
     data-price="{% if active_variant %}{{ active_variant.price|toman }}{% endif %}">

{# the disabled desktop add-to-cart button becomes: #}
    <button type="button" data-cart-add
            class="btn btn-primary flex-1 h-10 min-h-10 hidden lg:inline-flex disabled:bg-base-300 disabled:text-base-content disabled:border"
            {% if not active_variant or active_variant.max_orderable == 0 %}disabled{% endif %}
            aria-label="افزودن به سبد خرید">
      {% icon "shopping-cart" size=18 %}
      <span data-cart-label>افزودن به سبد</span>
    </button>
{# the heart button stays disabled (P4) #}
```

**`templates/pages/product.html`** (نوار چسبان موبایل)

```html
    <button type="button" data-cart-add
            class="btn btn-primary flex-1 min-w-0 h-11 min-h-11 disabled:bg-base-300 disabled:text-base-content disabled:border"
            {% if not default_variant or default_variant.max_orderable == 0 %}disabled{% endif %}
            aria-label="افزودن به سبد خرید">
      {% icon "shopping-cart" size=18 class="shrink-0" %}
      <span data-cart-label class="text-small whitespace-nowrap">افزودن به سبد</span>
    </button>
    ...
      <span data-bar-price class="text-lead font-medium whitespace-nowrap tabular-nums">{{ product.min_price|toman }}</span>
```

**`templates/partials/_otp_code_step.html`**: روی `<form id="otp-verify-form" ...>` صفت `data-guest-cart` اضافه شود.

---

### گام ۷ — تست‌ها (فقط حیاتی)

**ریشه‌ی `conftest.py`**: فیکسچرهای `brand`, `root_category`, `child_category`, `product` از `apps/catalog/tests/conftest.py` به اینجا منتقل شوند و آن فایل حذف شود. بعد این‌ها اضافه شود:

```python
from apps.accounts.models import Address, User
from apps.cart import services as cart_services
from apps.orders.models import ShippingMethod
from apps.orders.services import place_order
from apps.payments.models import PaymentGateway


@pytest.fixture
def checkout_env(db, settings):
    """Dev gateway visible, SMS on console, and the seed rows a TransactionTestCase flush may have wiped."""
    settings.DEBUG = True
    settings.SMS_BACKEND = "console"
    method, _ = ShippingMethod.objects.get_or_create(
        code="tipax", defaults={"title": "ارسال با تیپاکس", "checkout_note": "پس‌کرایه", "max_weight_g": 100_000}
    )
    PaymentGateway.objects.get_or_create(code="fake", defaults={"title": "درگاه آزمایشی"})
    return method


@pytest.fixture
def buyer(db) -> User:
    return User.objects.create_user("09121230001", first_name="مریم", last_name="احمدی", national_code="0012345679")


@pytest.fixture
def address(buyer, province, city) -> Address:
    return Address.objects.create(
        user=buyer,
        recipient_name="مریم احمدی",
        recipient_mobile=buyer.mobile,
        province=province,
        city=city,
        address_text="خیابان ولیعصر",
        plate="12",
        postal_code="1234567890",
        is_default=True,
    )


@pytest.fixture
def cart_item(buyer, product, checkout_env):
    variant = product.variants.get()
    cart_services.set_quantity(buyer, variant.pk, 2)
    return variant


@pytest.fixture
def placed_order(buyer, address, cart_item, checkout_env):
    lines, _ = cart_services.normalize(cart_services.get_cart(buyer))
    return place_order(
        user=buyer,
        address=address,
        method=checkout_env,
        buyer_form=None,
        seen_fingerprint=cart_services.fingerprint(lines),
    )
```

**`apps/cart/tests/test_cart.py`**

```python
import pytest

from apps.cart import services
from apps.cart.models import CartItem
from apps.catalog.models import Variant

pytestmark = pytest.mark.django_db


def test_quantity_is_clamped_to_max_orderable_and_zero_removes(buyer, product):
    variant = product.variants.get()
    Variant.objects.filter(pk=variant.pk).update(max_per_order=2)

    notice = services.set_quantity(buyer, variant.pk, 5)

    assert CartItem.objects.get(cart__user=buyer).qty == 2
    assert notice
    services.set_quantity(buyer, variant.pk, 0)
    assert not CartItem.objects.filter(cart__user=buyer).exists()


def test_merge_takes_the_max_never_the_sum_and_skips_unsellable(buyer, product):
    variant = product.variants.get()
    sold_out = Variant.objects.create(product=product, sku="WM-1234-B", title="مشکی", price=1_000, stock=0)
    services.set_quantity(buyer, variant.pk, 3)

    for _ in range(2):  # a repeated sync changes nothing
        services.merge_guest_items(buyer, [(variant.pk, 2), (sold_out.pk, 1)])
    assert dict(CartItem.objects.filter(cart__user=buyer).values_list("variant_id", "qty")) == {variant.pk: 3}

    services.merge_guest_items(buyer, [(variant.pk, 4)])
    assert CartItem.objects.get(cart__user=buyer).qty == 4
```

**اضافه به `apps/accounts/tests/test_login_views.py`** (در `TestVerifyCode`؛ `import json` و `from apps.cart.models import CartItem` بالای فایل):

```python
    def test_guest_cart_is_merged_before_the_redirect(self, client, fixed_otp_code, product):
        variant = product.variants.get()
        _request_code(client)

        client.post(
            reverse("accounts:otp_verify"),
            {"mobile": MOBILE, "code": fixed_otp_code, "guest_cart": json.dumps([{"v": variant.pk, "q": 2}])},
            HTTP_HX_REQUEST="true",
        )

        user = User.objects.get(mobile=MOBILE)
        assert list(CartItem.objects.filter(cart__user=user).values_list("variant_id", "qty")) == [(variant.pk, 2)]
```

**`apps/orders/tests/test_checkout.py`**

```python
import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Address, User
from apps.cart import services as cart_services
from apps.catalog.models import StockMovement, Variant
from apps.core.testing import find_ascii_digits
from apps.orders import services
from apps.orders.models import Order

pytestmark = pytest.mark.django_db


def _fingerprint(user) -> str:
    lines, _ = cart_services.normalize(cart_services.get_cart(user))
    return cart_services.fingerprint(lines)


def _place(user, address, method, fingerprint=None):
    return services.place_order(
        user=user, address=address, method=method, buyer_form=None, seen_fingerprint=fingerprint or _fingerprint(user)
    )


def test_order_reserves_stock_and_is_a_snapshot(placed_order, product):
    variant = Variant.objects.get(pk=product.variants.get().pk)
    assert variant.stock == 3
    assert StockMovement.objects.get(variant=variant).delta == -2
    assert (placed_order.payable, placed_order.shipping_cost) == (2 * 46_800_000, 0)
    assert placed_order.shipping_payment_mode == "collect"

    variant.price = 1
    variant.save()
    product.title = "عنوان دیگر"
    product.save()
    item = placed_order.items.get()
    assert (item.unit_price, item.product_title) == (46_800_000, "ماشین لباسشویی بوش مدل WM-1234")


def test_changed_price_blocks_the_order(buyer, address, cart_item, checkout_env):
    seen = _fingerprint(buyer)
    cart_item.price += 1
    cart_item.save()

    with pytest.raises(services.CheckoutError) as exc:
        _place(buyer, address, checkout_env, seen)

    assert exc.value.changed
    assert not Order.objects.exists()
    assert Variant.objects.get(pk=cart_item.pk).stock == 5


def test_overweight_order_is_blocked(buyer, address, cart_item, checkout_env):
    Variant.objects.filter(pk=cart_item.pk).update(weight_g=60_000)  # 2 x 60 kg > 100 kg

    with pytest.raises(services.CheckoutError):
        _place(buyer, address, checkout_env)

    assert not Order.objects.exists()


def test_checkout_never_overwrites_a_filled_profile(client, buyer, address, cart_item, checkout_env):
    client.force_login(buyer)

    response = client.post(
        reverse("orders:place"),
        {
            "address_id": address.pk,
            "gateway": "fake",
            "fingerprint": _fingerprint(buyer),
            "first_name": "دیگری",
            "national_code": "1234567891",
            "national_code_confirm": "on",
        },
    )

    buyer.refresh_from_db()
    assert response.status_code == 302
    assert (buyer.first_name, buyer.national_code) == ("مریم", "0012345679")


def test_new_checkout_cancels_the_previous_pending_order(buyer, address, placed_order, checkout_env):
    variant = placed_order.items.get().variant
    cart_services.set_quantity(buyer, variant.pk, 1)

    _place(buyer, address, checkout_env)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.CANCELLED
    assert Variant.objects.get(pk=variant.pk).stock == 4  # first reservation returned, second taken


def test_expiry_returns_stock_exactly_once(placed_order):
    Order.objects.filter(pk=placed_order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))
    variant = placed_order.items.get().variant

    assert services.expire_order(placed_order.pk) is True
    assert services.expire_order(placed_order.pk) is False

    assert Variant.objects.get(pk=variant.pk).stock == 5
    assert Order.objects.get(pk=placed_order.pk).status == Order.EXPIRED


@pytest.mark.django_db(transaction=True)
def test_last_unit_goes_to_exactly_one_buyer(product, province, city, checkout_env):
    variant = product.variants.get()
    Variant.objects.filter(pk=variant.pk).update(stock=1)
    buyers = []
    for mobile in ("09121230011", "09121230012"):
        user = User.objects.create_user(mobile, first_name="الف", last_name="ب", national_code="0012345679")
        address = Address.objects.create(
            user=user,
            recipient_name="الف",
            recipient_mobile=mobile,
            province=province,
            city=city,
            address_text="خیابان",
            plate="1",
            postal_code="1234567890",
            is_default=True,
        )
        cart_services.set_quantity(user, variant.pk, 1)
        buyers.append((user, address, _fingerprint(user)))

    results, barrier = [], threading.Barrier(2)

    def attempt(user, address, fingerprint):
        try:
            barrier.wait()
            results.append(_place(user, address, checkout_env, fingerprint).pk)
        except services.CheckoutError:
            results.append(None)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt, args=args) for args in buyers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len([r for r in results if r]) == 1
    assert Order.objects.count() == 1
    assert Variant.objects.get(pk=variant.pk).stock == 0


def test_cart_checkout_and_order_pages_show_persian_digits(client, buyer, placed_order):
    client.force_login(buyer)
    urls = [
        reverse("cart:detail"),
        reverse("orders:checkout"),
        reverse("orders:list"),
        reverse("orders:detail", args=[placed_order.number]),
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, url
        text, inputs = find_ascii_digits(response.content.decode())
        assert not text, f"ASCII digits on {url}: {text}"
        assert not inputs, f"ASCII digit inputs on {url}: {inputs}"
```

**`apps/payments/tests/test_payments.py`**

```python
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.cart.models import CartItem
from apps.catalog.models import Product, Variant
from apps.notifications.models import SmsLog
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments import gateways
from apps.payments import services as payment_services
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def payment(placed_order) -> Payment:
    payment_services.start(placed_order, "fake")
    return Payment.objects.get(order=placed_order)


def _callback(client, authority, ok=True):
    return client.get(
        reverse("payments:callback", args=["fake"]), {"Authority": authority, "Status": "OK" if ok else "NOK"}
    )


def _expire(order):
    Order.objects.filter(pk=order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))
    assert order_services.expire_order(order.pk)


def test_repeated_callback_pays_the_order_once(
    client, buyer, payment, placed_order, product, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        for _ in range(3):
            _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.PAID
    assert Payment.objects.filter(status=Payment.VERIFIED).count() == 1
    assert SmsLog.objects.filter(kind="order_paid").count() == 1
    assert Product.objects.get(pk=product.pk).purchase_count_total == 2
    assert not CartItem.objects.filter(cart__user=buyer).exists()


def test_failed_verification_keeps_the_order_pending_and_reserved(client, payment, placed_order, product, monkeypatch):
    monkeypatch.setattr(gateways.FakeGateway, "verify", lambda self, **kwargs: gateways.VerifyResult(False))

    _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.PENDING
    assert Payment.objects.get(pk=payment.pk).status == Payment.FAILED
    assert Variant.objects.get(pk=product.variants.get().pk).stock == 3
    assert not SmsLog.objects.exists()


def test_cancelled_payment_can_be_retried_within_the_reservation(client, payment, placed_order):
    _callback(client, payment.authority, ok=False)

    placed_order.refresh_from_db()
    assert Payment.objects.get(pk=payment.pk).status == Payment.CANCELLED
    assert placed_order.status == Order.PENDING and placed_order.can_pay_now


def test_payment_after_expiry_takes_the_stock_back(client, payment, placed_order, product):
    _expire(placed_order)
    assert Variant.objects.get(pk=product.variants.get().pk).stock == 5

    _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.PAID
    assert Variant.objects.get(pk=product.variants.get().pk).stock == 3


def test_payment_after_expiry_without_stock_is_recorded_not_lost(client, payment, placed_order, product):
    _expire(placed_order)
    Variant.objects.filter(pk=product.variants.get().pk).update(stock=1)  # someone else bought it meanwhile

    _callback(client, payment.authority)

    placed_order.refresh_from_db()
    assert placed_order.status == Order.EXPIRED  # a human refunds; the verified payment stays on record
    assert Payment.objects.get(pk=payment.pk).status == Payment.VERIFIED


def test_expiry_skips_an_order_whose_payment_is_being_verified(payment, placed_order):
    Payment.objects.filter(pk=payment.pk).update(status=Payment.VERIFYING)
    Order.objects.filter(pk=placed_order.pk).update(reserved_until=timezone.now() - timedelta(minutes=1))

    assert order_services.expire_order(placed_order.pk) is False


def test_dev_gateway_is_hidden_outside_debug(client, checkout_env, settings):
    settings.DEBUG = False

    assert "fake" not in [g.code for g in gateways.available()]
    assert client.get(reverse("payments:fake_bank", args=["FAKE1"])).status_code == 404


def test_zarinpal_sends_rials_and_accepts_an_already_verified_payment(monkeypatch, settings):
    settings.ZARINPAL_SANDBOX = True
    settings.ZARINPAL_MERCHANT_ID = ""
    sent = []

    def fake_post(self, path, body):
        sent.append((path, body))
        if path == "request":
            return {"data": {"code": 100, "authority": "S000"}, "errors": []}
        return {"data": {"code": 101, "ref_id": 7, "card_pan": "502229******5995"}, "errors": []}

    monkeypatch.setattr(gateways.ZarinpalGateway, "_post", fake_post)
    gateway = gateways.ZarinpalGateway()

    started = gateway.request(
        amount=46_800_000, callback_url="http://x/cb", description="d", mobile="09121234567", order_number="ML-1"
    )
    verified = gateway.verify(authority="S000", amount=46_800_000)

    assert sent[0][1]["amount"] == 468_000_000 and sent[0][1]["currency"] == "IRR"
    assert started.redirect_url == "https://sandbox.zarinpal.com/pg/StartPay/S000"
    assert verified.ok and sent[1][1]["amount"] == 468_000_000
```

---

### گام ۸ — بازنویسی تست موجود و ابزارها

در `apps/catalog/tests/test_variant_limits.py` تست `test_shipping_note_comes_from_settings` با این جایگزین شود (متن ارسال حالا از `ShippingMethod` می‌آید و `SiteSettings.shipping_note` فقط fallback است؛ `from apps.orders.models import ShippingMethod` بالای فایل):

```python
@pytest.mark.django_db
def test_shipping_note_comes_from_the_active_method_with_settings_as_fallback(
    client, product, django_capture_on_commit_callbacks
):
    from apps.core.models import SiteSettings

    ShippingMethod.objects.all().delete()
    with django_capture_on_commit_callbacks(execute=True):
        method = ShippingMethod.objects.create(code="t1", title="تیپاکس", product_note="کرایه با گیرنده")
    assert "کرایه با گیرنده" in client.get(product.get_absolute_url()).content.decode()

    with django_capture_on_commit_callbacks(execute=True):
        method.delete()
        site = SiteSettings.get_solo()
        site.shipping_note = "ارسال آزمایشی با پیک"
        site.save()
    body = client.get(product.get_absolute_url()).content.decode()
    assert "ارسال آزمایشی با پیک" in body and "کرایه با گیرنده" not in body
```

---

### گام ۹ — به‌روزرسانی اسناد (همین فاز، نه بعداً)

- **`docs/03` بخش ۳:** مدل‌های `cart`/`orders`/`payments` با کد واقعی هم‌تراز شوند. `Order` بدون `placed_at`/`discount_total`/`customer_note`؛ `ShippingMethod` فقط فیلدهای v1؛ `Payment.status` شامل `verifying`؛ `PaymentGateway` طبق کد. یادداشت: موجودی هنگام ساخت سفارش با `reason="order"` کم می‌شود و پرداخت حرکت جدیدی ثبت نمی‌کند؛ `order_item_id` عددی می‌ماند. ردیف تغییرات: «۰.۳.۶ (P3)».
- **`docs/02`:** در بخش ۶ و ۷ تصمیم‌های جدول بخش ۰ این بریف ثبت شود (گیرنده روی آدرس، ایمیل در checkout نیست، یک سفارش `pending_payment` برای هر کاربر، badge سبد = تعداد خط‌ها، ادغام سبد هنگام تایید OTP). نسخه‌ی سند و «بسته‌شده در ۰.۶».
- **`docs/08-ui-modules.md`:** ردیف `cart` / `cart.js` با API (`MM.cart.read()`، `MM.cart.clear()`) و قرارداد HTML (`[data-cart-add]`، `[data-cart-label]`، `[data-cart-set]` با `data-variant` و `data-qty`، `[data-cart-items]`، `[data-guest-cart]`، `#cart-content`، `#cart-state`، `#variant-panel[data-variant-id|data-max|data-orderable|data-price]`، `[data-bar-price]`) و خط در «تغییرات». بدون این ردیف تست `test_every_mm_module_is_documented` رد می‌شود.
- **`docs/vendors/zarinpal/`:** نتیجه‌ی تطبیق `[VERIFY]` (آدرس StartPay، sandbox، حداقل مبلغ) در یک یادداشت کوتاه.
- **`CLAUDE.md`:** بخش ۷ خط `expire_orders`؛ بخش ۸ اپ‌های `cart`، `orders`، `payments`.
- **`docs/01`:** بدون تغییر (A4 و B7 هنوز در انتظارند و بلوکه‌کننده نیستند).
- **`docs/phases/STATUS.md`:** ردیف P3 و موارد باز: پرداخت موفق روی سفارش `expired` بدون موجودی و پرداخت تکراری فقط `logger.error` می‌شود؛ P6 باید گزارش «`Payment` تاییدشده روی سفارش غیر `paid`» را در ادمین بسازد.

---

## ۴. خارج از این فاز

متن‌های اجتماعی سبد و checkout و قلب (P4)، تغییر وضعیت با کد رهگیری، پیامک ارسال و فاکتور (P6)، کد تخفیف، ریورس و بازگشت وجه (دستی در v1)، ثبت `ProductDailyStat` (P4؛ فعلاً فقط شمارنده‌های `purchase_count_*`).

---

## ۵. Definition of Done (قابل راستی‌آزمایی توسط Claude Code)

- [ ] `uv run pytest` سبز؛ `uv run ruff check .` و `uv run ruff format --check .` بدون خروجی.
- [ ] `uv run python manage.py makemigrations --check --dry-run` بدون تغییر؛ `make sprite` بدون خطا؛ `pnpm run build:css` اجرا شده.
- [ ] هیچ تماس شبکه داخل `transaction.atomic()` نیست. `rg -n "urlopen|send_template" apps/orders apps/payments apps/cart` فقط `gateways.py` (`urlopen`) و `_notify_paid` (که با `on_commit` زمان‌بندی می‌شود) را نشان بدهد. کد `orders/services.py` و `payments/services.py` را هم یک‌بار بخوان و تایید کن.
- [ ] `rg -n "\.update\(" apps | rg "Variant|Product"` بیرون از `stock.py`، `models.py`، `cache.py` و `tree.py` صفر است (تست معماری هم همین را می‌گیرد).
- [ ] grepهای `docs/04` بخش ۱۳ روی `templates/` و `static/src/` صفر؛ `rg -n "alert\(|confirm\(|prompt\(" templates static/js` صفر.
- [ ] تست‌های رقابت روی فایل SQLite واقعی اجرا و پاس شده‌اند.
- [ ] `docs/` و `CLAUDE.md` طبق گام ۹ به‌روز شده‌اند.
- [ ] موارد `[VERIFY]` درگاه تطبیق داده شد یا در گزارش به‌عنوان باز ثبت شد.

---

## ۶. فهرست بررسی چشمی (Claude Code نگاه نمی‌کند؛ فقط همین فهرست را در گزارش می‌آورد و کاربر خودش می‌بیند)

برای هر مورد، تم روشن و تاریک و عرض‌های ۳۲۰ و ۱۲۸۰:

1. **صفحه‌ی محصول:** «افزودن به سبد» برای مهمان و کاربر؛ حالت «در سبد شما»؛ تغییر variant، یعنی قیمت نوار موبایل عوض می‌شود و دکمه برای variant ناموجود غیرفعال می‌شود؛ پیام سقف تعداد.
2. **هدر و dock:** شمارنده‌ی سبد در صفر پنهان است و با افزودن به‌روز می‌شود؛ پرش layout ندارد.
3. **سبد (مهمان):** اسکلت بارگذاری بدون پرش؛ ردیف‌ها، stepper (آیکون سطل وقتی تعداد ۱ است)، سقف تعداد، ردیف ناموجود؛ کاشی تصویر پس‌زمینه‌ی سفید.
4. **سبد (کاربر):** همان موارد؛ نوار چسبان پایین موبایل (دکمه سمت راست، جمع سمت چپ، قیمت نشکسته) بالای dock؛ محتوا زیر نوار نمی‌رود.
5. **ورود از سبد:** «ادامه‌ی خرید» برای مهمان مودال ورود را باز می‌کند؛ بعد از تایید کد، سبد حفظ شده و مستقیم به checkout می‌رسد.
6. **Checkout:** فقط فیلدهای خالی پروفایل دیده می‌شوند؛ هشدار و چک‌باکس کد ملی؛ انتخاب آدرس؛ افزودن آدرس درون صفحه، شامل Select شهر وابسته، نقشه‌ی نشان در صورت وجود کلید، و برگشتن به لیست با آدرس تازه انتخاب‌شده؛ روش ارسال و متن پس‌کرایه؛ انتخاب درگاه؛ خلاصه‌ی سفارش؛ نوار چسبان «پرداخت».
7. **خطاها در checkout:** پیام قیمت یا موجودی تغییر کرد، آدرس انتخاب‌نشده، وزن بیش از سقف (پیام و دکمه‌ی غیرفعال).
8. **درگاه آزمایشی:** صفحه‌ی پرداخت موفق و انصراف و بازگشت به نتیجه‌ی سفارش.
9. **نتیجه‌ی سفارش و جزئیات:** نقطه‌ی وضعیت و متن کنار آن؛ جمله‌ی پس‌کرایه؛ دکمه‌ی «پرداخت» و نوار چسبان برای سفارش در انتظار پرداخت؛ فاصله‌ها و ارقام فارسی.
10. **لیست سفارش‌ها:** کارت‌ها، وضعیت خالی، تب «سفارش‌ها» در ناوبری حساب.
11. **صفحه‌ی `processing`:** متن و دکمه‌ها.
12. **sandbox زرین‌پال (اگر شبکه هست):** یک پرداخت موفق و یک انصراف از ابتدا تا انتها.

---

## گزارش پایانی (قالب)

در پایان فاز در چند خط فارسی بگو: چه ساخته شد، کدام `[ASSUMPTION]` و `[VERIFY]` باز ماند، چه چیزی از کاربر لازم است (مرچنت‌کد، لوگوی زرین‌پال، شناسه‌ی قالب `ORDER_PAID`، همه غیرمسدودکننده)، فهرست بخش ۶ برای بررسی چشمی، و قدم بعد (P4).
