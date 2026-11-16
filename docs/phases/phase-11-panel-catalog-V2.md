# فاز P11 — محصولات، دسته‌ها و برندها

**هدف:** کارمند محتوا همه‌ی کار روزانه‌ی کاتالوگ را از `/panel/` انجام دهد: ساخت محصول با «استودیوی محصول»، گالری، تنوع و قیمت، مشخصات فنی، انتشار، دسته‌ها و برندها. هر نوشتن از `save()` مدل‌ها می‌گذرد تا `rev`، `subtree_rev`، ایندکس FTS و aggregateها درست بمانند.

**نکات کلی این بریف:**
- بخش ۰ نقص‌های واقعی P10 را ترمیم می‌کند. تا آن سبز نشود به بقیه نرو.
- بررسی چشمی با من است. Claude Code مرورگر، Playwright و اسکرین‌شات اجرا نمی‌کند و در پایان فقط فهرست بخش ۱۰ را تحویل می‌دهد.
- تست فقط برای پول، موجودی، مجوز، امنیت و باطل‌سازی کش نوشته می‌شود. تست مارک‌آپ یا رفتار خود فریم‌ورک ممنوع است (بخش ۶).

---

## ۰. ترمیم ورودی (باقی‌مانده‌ی P10)

گزارش آخر درست است: `ImportError` از `apps/cart/views.py` واقعی است. بررسی کدی که فرستاده‌ای چند نقص دیگر هم نشان داد که با همان ریشه (اجرای ناقص بریف P10-V2) پیدا شده‌اند:

| # | نقص | اثر |
|---|-----|-----|
| ۱ | `apps/orders/shipping.py` فقط `recipient_text` و `map_link` دارد؛ `default_method`، `product_page_note`، `has_tracking` و `tracking_page` حذف شده‌اند | `ImportError` در سبد، checkout، صفحه‌ی محصول، `check_launch`، `workflow` و `notify` |
| ۲ | در `apps/orders/admin.py` تابع `_staff_targets` داخل کلاس `OrderStatusLogInline` تورفته است | `NameError` در `StatusForm` و `change_view` |
| ۳ | `apps/panel/apps.py` متد `ready()` ندارد | provider جستجو و بج‌ها هرگز ثبت نمی‌شوند |
| ۴ | `templates/panel/*` نسخه‌ی خراب قبلی است: سینتکس Jinja در `base.html`، `{% endif %}` ناقص، فیلتر ناموجود `jalali_str`، فیلد ناموجود `item.total_price`، و `shell.html`، `403.html`، `account.html`، `badge.html` و ... وجود ندارند | هر صفحه‌ی پنل خطا می‌دهد |
| ۵ | `templates/partials/_mm_dialog.html` یک دیالوگ ساده است و قرارداد `MM.ui` را ندارد | `confirm` در پنل کار نمی‌کند |
| ۶ | `static/js/mm/panel.js` هنوز `alert()` دارد | `test_ui_rules` رد می‌کند (D31) |
| ۷ | `.fb-muted` و `.font-technical` در `input.css` نیستند | تقویم شمسی بدون استایل |
| ۸ | تست‌های P10 (`test_access`، `test_queries`، `test_refund`) ساخته نشده‌اند | پوشش پول و مجوز صفر است |

### ۰.۱ `apps/orders/shipping.py` (جایگزین کامل)

اول `git show HEAD~1:apps/orders/shipping.py` یا `git log -p -- apps/orders/shipping.py` را بخوان. هر تابع دیگری که قبلاً بوده و جز چهار تابع زیر استفاده می‌شود هم برگردد. بعد این را اجرا کن و خروجی را با فهرست زیر تطبیق بده:

```
rg -n "orders\.shipping|orders import shipping|shipping\.(default_method|product_page_note|has_tracking|tracking_page|recipient_text|map_link)" apps config
```

```python
"""Shipping helpers: the active method, page text, tracking, and what staff paste into the Tipax panel."""

from __future__ import annotations

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod

# [VERIFY] docs/vendors/neshan/: replace with a documented share link if there is one.
MAP_LINK = "https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"
# docs/vendors/tipax/08: only the public tracking page is documented; the customer types the code there.
TIPAX_TRACKING_PAGE = "https://tipaxco.com/tracking"


def default_method() -> ShippingMethod | None:
    """The method checkout uses: the first active one. None means shipping is off and checkout is blocked."""
    return ShippingMethod.objects.filter(is_active=True).order_by("sort", "pk").first()


def product_page_note() -> str:
    """Shipping line of the product page: the active method's text, with SiteSettings.shipping_note as fallback."""
    method = default_method()
    if method is not None and method.product_note:
        return method.product_note
    return SiteSettings.get_solo().shipping_note


def has_tracking(order) -> bool:
    """Whether this order's method issues a tracking code. A deleted method keeps the v1 default (Tipax: yes)."""
    method = order.shipping_method
    return True if method is None else method.has_tracking


def tracking_page(order) -> str:
    """Public tracking page to link next to the code; '' when there is no code or no known carrier page."""
    if not order.tracking_code:
        return ""
    method = order.shipping_method
    code = method.code if method is not None else ""
    if code == "tipax" or "تیپاکس" in (order.shipping_method_title or ""):
        return TIPAX_TRACKING_PAGE
    return ""


def recipient_text(order) -> str:
    """What staff paste into the Tipax panel: plain lines. ASCII digits on purpose (an outside system; D30 is for our screens)."""
    unit = f"، واحد {order.unit}" if order.unit else ""
    return "\n".join(
        [
            order.recipient_name,
            order.recipient_mobile,
            f"{order.province_name}، {order.city_name}",
            f"{order.address_text}، پلاک {order.plate}{unit}",
            f"کدپستی: {order.postal_code}",
        ]
    )


def map_link(order) -> str:
    if order.lat is None or order.lng is None:
        return ""
    return MAP_LINK.format(lat=f"{order.lat:.6f}", lng=f"{order.lng:.6f}")
```

### ۰.۲ `apps/orders/admin.py`

`_staff_targets` را از داخل کلاس بیرون بیاور و بین `OrderStatusLogInline` و `StatusForm` به‌صورت تابع سطح ماژول بگذار. محتوایش عوض نمی‌شود:

```python
class OrderStatusLogInline(_ReadOnlyInline):
    model = OrderStatusLog
    fields = ("from_status", "to_status", "note", "created_at")
    readonly_fields = ("created_at",)


def _staff_targets(order) -> list[str]:
    """Refunds are recorded on the payment (payments.services.record_refund), never as a bare status move."""
    return [target for target in workflow.allowed_targets(order) if target != Order.REFUNDED]


class StatusForm(forms.Form):
    ...
```

### ۰.۳ `apps/panel/apps.py`

```python
from __future__ import annotations

from django.apps import AppConfig


class PanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.panel"
    verbose_name = "پنل مدیریت"

    def ready(self) -> None:
        from apps.panel import providers  # noqa: F401  (registers search providers and navigation badges)
```

### ۰.۴ دیالوگ مشترک

بلوک `<dialog id="mm-dialog">…</dialog>` را از `templates/base.html` ببر داخل `templates/partials/_mm_dialog.html` (بدون تغییر محتوا) و در `base.html` جایش `{% include "partials/_mm_dialog.html" %}` بگذار. محتوای جدید فایل دقیقاً این است:

```html
<dialog id="mm-dialog" class="modal modal-bottom sm:modal-middle" aria-labelledby="mm-dialog-title" aria-describedby="mm-dialog-message">
  <div class="modal-box max-w-sm p-5 bg-base-100 rounded-t-box sm:rounded-box">
    <h2 id="mm-dialog-title" data-mm-title class="text-lead font-medium" hidden></h2>
    <p id="mm-dialog-message" data-mm-message class="text-small text-ink-2 mt-2"></p>
    <div class="flex items-center gap-2 border-t pt-4 mt-4">
      <button type="button" data-mm-ok class="btn btn-primary flex-1 min-w-0 h-11 min-h-11"></button>
      <button type="button" data-mm-cancel class="btn btn-ghost h-11 shrink-0 text-ink-2"></button>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button aria-label="بستن">بستن</button></form>
</dialog>
```

### ۰.۵ قالب‌ها، JS و CSS

همه‌ی کدهای زیر در `docs/phases/phase-10-panel-orders-V2.md` هستند. آن فایل را باز کن و **عیناً** اعمال کن.

- فایل‌های `templates/panel/**` که الان در مخزن هست حذف و از بخش ۵.۳ همان سند ساخته شود. `partials/login_form.html` حذف شود و جایش چیزی نمی‌آید.
- `static/js/mm/panel.js` نسخه‌ی این بریف است (بخش ۴.۳). نسخه‌ی V2 را نگیر.
- دو کلاس `.fb-muted` و `.font-technical` از V2 بخش ۵.۴ به `static/src/input.css` اضافه شود و `pnpm run build:css` اجرا شود.

یک اصلاح لازم دارد (اشتباه خودِ V2): در `panel/orders/list.html` و `panel/payments/list.html` ویژگی `data-date-range` روی `<form>` است. اعتبارسنجی بازه با `form.querySelectorAll('[data-date-range]')` کار می‌کند و خود form را پیدا نمی‌کند. دو ورودی تاریخ و پیام خطا را داخل یک `div` بگذار:

```html
<div class="contents" data-date-range>
  <input type="text" name="from" ...>
  <input type="text" name="to" ...>
  <span class="hidden text-label text-error" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد</span>
</div>
```

### ۰.۶ تست‌های P10 و `conftest` پنل

اگر نیستند، `apps/panel/tests/conftest.py`، `test_access.py`، `test_queries.py` و `apps/payments/tests/test_refund.py` را عیناً از V2 بخش ۵.۵ بساز. `test_access.py` دکوراتور هر URL پنل را می‌سنجد و URLهای P11 را هم خودکار می‌گیرد.

### ۰.۷ گیت ورود به P11

`uv run python manage.py check` و `uv run pytest` و `uv run ruff check .` باید سبز باشند. تا سبز نشده‌اند کد P11 ننویس. اگر خطای دیگری دیدی، ریشه‌اش را در بخش ۰ برطرف کن و در گزارش بنویس.

---

## ۱. مطالعه

- `docs/09-panel-spec.md` ماژول‌های ۴، ۵، ۶ و بخش‌های ۲.۵ و ۲.۷
- `docs/10-panel-ui.md`، `docs/04` بخش ۴.۱ و ۹.۴ و ۱۳، `docs/08`
- `docs/03-data-model.md` بخش ۵ (کش و باطل‌سازی)
- کد: `apps/catalog/{models,cache,images,stock,tree,constants,search_text}.py`، `apps/core/{html,text,widgets,forms}.py`، `apps/panel/*`، `apps/catalog/tests/test_architecture.py`، `apps/catalog/admin.py`
- اسکیل‌ها: `htmx-patterns`، `daisyui` (card، tabs، fieldset، file-input، progress)، `unslop` چک‌لیست انتها

---

## ۲. تصمیم‌های فاز (همه `[ASSUMPTION]`، در `docs/09` ثبت شوند)

1. **استودیو:** هر بخش (پایه، تنوع، گالری، مشخصات) فرم و ذخیره‌ی جدا و پاسخ HTMX جدا دارد. ستون کناری (وضعیت، چک‌لیست، آمار) بعد از هر ذخیره با OOB تازه می‌شود.
2. **تغییر دسته در بخش پایه:** بعد از ذخیره، بخش مشخصات با OOB عوض می‌شود. پیش‌نمایش زنده ندارد.
3. **دسته‌ها و برندها** به‌جای مودال یا کشو صفحه‌ی فرم جدا دارند (PRG). درخت دسته باز و بسته نمی‌شود؛ ↑↓ فقط `menu_order` را جابه‌جا می‌کند و `featured_order` فیلد عددی فرم است.
4. **ویرایش سریع** فقط قیمت و قیمت قبل از تخفیف همه‌ی تنوع‌هاست.
5. **موجودی:** در P11 فقط «موجودی اولیه‌ی تنوع تازه» با `stock.increment(reason="manual")` ثبت می‌شود. تغییر بعدی موجودی کار `stock.adjust_manual` در P12 است.
6. **توضیحات محصول (D46):** textarea. متن بدون تگ HTML خودکار پاراگراف می‌شود و همه‌چیز با `sanitize_html` پاک می‌شود. ویرایشگر غنی ساخته نمی‌شود، چون Claude Code بدون مرورگر نمی‌تواند RTL و ارقام فارسی آن را بسنجد. فقط در پایان فاز از کاربر پرسیده شود (بخش ۸).
7. **حذف محصول:** فقط پیش‌نویس بدون `OrderItem`، بدون `purchase_count_total` و بدون ردیف `StockMovement` (چون `PROTECT` است). بقیه بایگانی می‌شوند. تنوع دارای گردش موجودی حذف نمی‌شود و فقط غیرفعال می‌شود.
8. **کلیدهای `Variant.options`:** `color` و `model`. کلیدهای دیگر دست‌نخورده می‌مانند. SKU با الگوی `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`. سقف `max_per_order` برابر ۹۹۹ است.
9. **مجوزها:** گروه «محتوا» در `setup_groups` همه‌ی مجوزهای لازم را دارد، پس `setup_groups` در این فاز تغییر نمی‌کند. ویرایش دسته و برند مجوز `change_*` می‌خواهد (صفحه‌ی فرم)، اما استودیوی محصول با `view_product` باز می‌شود و بخش‌ها بدون مجوز `disabled` می‌مانند.

---

## ۳. دامنه (`apps/catalog`)

### ۳.۱ `apps/catalog/images.py` (جایگزین کامل)

اصلاح EXIF (عکس موبایل چرخیده رندر نشود) و اعتبارسنجی بارگذاری:

```python
"""WebP renditions and upload checks for catalog images (docs/phases P1 task 10, P11)."""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, ImageOps

from apps.catalog.constants import IMAGE_WIDTHS
from apps.core.jalali import to_fa_digits

logger = logging.getLogger(__name__)

UPLOAD_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def generate_webp_sizes(image_field, widths: tuple[int, ...] = IMAGE_WIDTHS) -> dict[str, str]:
    """Generate resized WebP files and return ``{width: relative path}``."""
    source = Path(image_field.path)
    with Image.open(source) as opened:
        # Phone photos store their rotation in EXIF; without this the renditions come out sideways.
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_width = image.width
        result: dict[str, str] = {}
        for width in widths:
            if width > original_width * 1.5:
                continue
            height = max(1, round(image.height * width / image.width))
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            target = source.with_name(f"{source.stem}-{width}.webp")
            resized.save(target, format="WEBP", quality=82, method=4)
            result[str(width)] = str(target.relative_to(Path(settings.MEDIA_ROOT))).replace("\\", "/")
    return result


def validate_upload(file, *, max_bytes: int, label: str = "تصویر") -> tuple[str, int, int]:
    """Check an uploaded image. Returns (extension, width, height) or raises ValidationError with a Persian message."""
    if file.size > max_bytes:
        raise ValidationError(f"حجم {label} نباید بیشتر از {to_fa_digits(max_bytes // (1024 * 1024))} مگابایت باشد")
    try:
        file.seek(0)
        with Image.open(file) as probe:
            probe.verify()
        file.seek(0)
        with Image.open(file) as image:
            image_format, (width, height) = image.format, image.size
    except Exception as exc:  # Pillow raises several unrelated types for broken or hostile files
        raise ValidationError(f"{label} معتبر نیست") from exc
    finally:
        file.seek(0)
    if image_format not in UPLOAD_FORMATS:
        raise ValidationError(f"{label} باید jpg، png یا webp باشد")
    return UPLOAD_FORMATS[image_format], width, height
```

### ۳.۲ `apps/catalog/publishing.py` (جدید)

```python
"""Publishing rules and gallery bookkeeping shared by the panel and the admin (docs/09 module 4)."""

from __future__ import annotations


def publish_checks(product) -> tuple[list[str], list[str]]:
    """(errors, warnings). An error blocks activation; a warning only informs."""
    errors: list[str] = []
    warnings: list[str] = []
    if not (product.title or "").strip():
        errors.append("عنوان محصول خالی است")
    if not product.category_id:
        errors.append("دسته‌بندی انتخاب نشده است")
    prices = product.variants.filter(is_active=True).values_list("price", flat=True)
    if not any(price > 0 for price in prices):
        errors.append("دست‌کم یک تنوع فعال با قیمت بیشتر از صفر لازم است")
    if not product.images.exists():
        warnings.append("محصول تصویر ندارد")
    if not (product.description or "").strip():
        warnings.append("توضیحات خالی است")
    if not product.brand_id:
        warnings.append("برند انتخاب نشده است")
    return errors, warnings


def sync_main_image(product, *, skip_pk: int | None = None) -> bool:
    """D40: the main image is always the first one by order. True when the product row changed.

    `skip_pk` is an image about to be deleted: the product must stop pointing at it first, otherwise
    SET_NULL would change the row behind the tracking and the list cache would stay stale.
    """
    images = product.images.order_by("sort", "pk")
    if skip_pk is not None:
        images = images.exclude(pk=skip_pk)
    first = images.first()
    if product.main_image_id == (first.pk if first else None):
        return False
    product.main_image = first
    product.save(update_fields=["main_image", "updated_at"])
    return True
```

### ۳.۳ `apps/catalog/specs.py` (جدید)

```python
"""Which specification attributes apply to a category (D41)."""

from __future__ import annotations

from decimal import Decimal

from apps.catalog.models import SpecAttribute


def applicable_attributes(category):
    """The category's own attributes plus its ancestors', as far up as each `spec_inherit` allows. Root first."""
    ids = [category.pk]
    node = category
    for parent in reversed(category.ancestors()):  # nearest parent first
        if not node.spec_inherit:
            break
        ids.append(parent.pk)
        node = parent
    return (
        SpecAttribute.objects.filter(category_id__in=ids)
        .select_related("category")
        .order_by("category__depth", "sort", "pk")
    )


def number_text(number: Decimal) -> str:
    """ASCII text of a number spec for `value_text` (facets read it): 9.50 -> '9.5', 100.00 -> '100'."""
    return format(number.normalize(), "f")
```

---

## ۴. پنل

### ۴.۱ ابزارهای کوچک

**`apps/panel/ordering.py`** (جدید):

```python
"""Up/down ordering for lists with a plain integer column (variants, images, categories)."""

from __future__ import annotations


def moved(items: list, pk: int, delta: int) -> list | None:
    """The list with `pk` moved by `delta` places, or None when it cannot move (already at the end)."""
    ids = [item.pk for item in items]
    if pk not in ids:
        return None
    index = ids.index(pk)
    target = index + delta
    if not 0 <= target < len(items):
        return None
    items = list(items)
    items[index], items[target] = items[target], items[index]
    return items


def to_front(items: list, pk: int) -> list:
    items = list(items)
    for index, item in enumerate(items):
        if item.pk == pk:
            items.insert(0, items.pop(index))
            break
    return items


def renumber(items: list, field: str = "sort") -> list:
    """Give the items 0, 1, 2 ... in list order. Returns only those whose value changed; the caller saves them."""
    changed = []
    for position, item in enumerate(items):
        if getattr(item, field) != position:
            setattr(item, field, position)
            changed.append(item)
    return changed
```

**`apps/panel/templatetags/panel_tags.py`** (جایگزین کامل؛ دو فیلتر تازه):

```python
from __future__ import annotations

from django import template
from django.conf import settings

from apps.panel import badges, nav
from apps.payments.models import Payment

register = template.Library()

PAYMENT_DOT = {Payment.VERIFIED: "status-success", Payment.VERIFYING: "status-info", Payment.FAILED: "status-error"}
PRODUCT_DOT = {"active": "status-success", "draft": "status-warning", "archived": "status-neutral"}


@register.inclusion_tag("panel/partials/sidebar.html", takes_context=True)
def render_sidebar(context, oob=False):
    request = context["request"]
    return {
        "groups": nav.visible_groups(request.user, request.path),
        "counts": badges.counts_for(request.user),
        "request": request,
        "oob": oob,
    }


@register.inclusion_tag("panel/partials/badge.html")
def render_badge(key: str, counts: dict[str, int]):
    count = counts.get(key, 0)
    return {"key": key, "count": count, "visible": count > 0}


@register.filter
def payment_dot(status: str) -> str:
    return PAYMENT_DOT.get(status, "status-neutral")


@register.filter
def product_dot(status: str) -> str:
    return PRODUCT_DOT.get(status, "status-neutral")


@register.filter
def thumb_url(image) -> str:
    """Smallest generated rendition of a ProductImage (falls back to the original file)."""
    if not image:
        return ""
    if image.widths:
        return f"{settings.MEDIA_URL}{image.widths[min(image.widths, key=int)]}"
    return image.image.url if image.image else ""
```

**`apps/panel/nav.py`**: این سه ردیف را به `ITEMS` اضافه کن (آیکون‌ها را `build_sprite.py` می‌گیرد؛ اگر نبود نزدیک‌ترین آیکون موجود):

```python
    NavItem("products", "محصولات", "panel:products", icon="package", group="catalog",
            perms=("catalog.view_product",)),
    NavItem("categories", "دسته‌ها", "panel:categories", icon="layout-grid", group="catalog",
            perms=("catalog.view_category",)),
    NavItem("brands", "برندها", "panel:brands", icon="tag", group="catalog",
            perms=("catalog.view_brand",)),
```

**`apps/panel/providers.py`**: این ایمپورت‌ها و provider را به فایل اضافه کن:

```python
from django.db.models import Q

from apps.catalog.models import Product, Variant
from apps.core.text import normalize_fa


@search.register("products", "محصولات", "catalog.view_product")
def find_products(query: str) -> list[search.Hit]:
    text = normalize_fa(query, for_search=True)
    if not text:
        return []
    rows = (
        Product.objects.filter(
            Q(search_text__contains=text) | Q(pk__in=Variant.objects.filter(sku__icontains=text).values("product_id"))
        )
        .select_related("brand")
        .order_by("-created_at")[: search.PER_PROVIDER]
    )
    return [
        search.Hit(
            product.title,
            f"{product.brand.name_fa + ' — ' if product.brand_id else ''}{product.get_status_display()}",
            reverse("panel:product_studio", args=[product.pk]),
        )
        for product in rows
    ]
```

### ۴.۲ `apps/panel/forms_catalog.py` (جدید)

```python
"""Catalog forms of the panel (docs/09 modules 4 to 6). Digits are shown Persian and stored ASCII (D30)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q
from django.utils.html import linebreaks
from django.utils.text import slugify

from apps.catalog.images import validate_upload
from apps.catalog.models import Brand, Category, Product, SpecAttribute, Variant
from apps.catalog.specs import number_text
from apps.catalog.tree import subtree_upper_bound
from apps.core.forms import FieldErrorAttrsMixin
from apps.core.html import sanitize_html
from apps.core.text import normalize_digits, normalize_fa
from apps.core.widgets import FaDigitsInput, FaTextarea, FaTextInput
from apps.panel.fields import FaIntegerField, TomanField

LOGO_MAX_BYTES = 2 * 1024 * 1024
SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SEPARATORS = re.compile(r"[\s,٬،_]")
FILE_ATTRS = {"class": "file-input w-full", "accept": "image/png,image/jpeg,image/webp"}
CHECKBOX = {"class": "checkbox checkbox-sm"}


def category_label(category) -> str:
    return f"{'— ' * category.depth}{category.name}"


def multiline(text: str) -> str:
    """Normalize per line so paragraphs survive (normalize_fa collapses all whitespace)."""
    lines = [normalize_fa(line) for line in (text or "").splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def rich_text(value: str) -> str:
    """Product description: plain text becomes paragraphs, everything goes through the whitelist sanitizer."""
    text = (value or "").strip()
    if text and "<" not in text:
        text = linebreaks(text, autoescape=True)
    return sanitize_html(text)


def clean_slug_value(form, raw, max_length: int) -> str:
    raw = (raw or "").strip()
    if not raw:
        return form.instance.slug  # empty: keep the current one; the model builds a slug on first save
    slug = slugify(raw, allow_unicode=True)[:max_length]
    if not slug:
        raise ValidationError("نشانی معتبر نیست")
    return slug


# --- products ---------------------------------------------------------------


class ProductCreateForm(FieldErrorAttrsMixin, forms.Form):
    title = forms.CharField(
        label="عنوان", max_length=255, widget=FaTextInput(attrs={"class": "input w-full", "data-autofocus": "1"})
    )
    category = forms.ModelChoiceField(
        label="دسته‌بندی",
        queryset=Category.objects.none(),
        empty_label="انتخاب دسته",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    brand = forms.ModelChoiceField(
        label="برند (اختیاری)",
        queryset=Brand.objects.none(),
        required=False,
        empty_label="بدون برند",
        widget=forms.Select(attrs={"class": "select w-full"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("path")
        self.fields["category"].label_from_instance = category_label
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True).order_by("name_fa")

    def clean_title(self) -> str:
        return normalize_fa(self.cleaned_data["title"])


class ProductBasicsForm(FieldErrorAttrsMixin, forms.ModelForm):
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=280,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
        help_text="خالی = ساخت خودکار از عنوان. نشانی قبلی با ریدایرکت ۳۰۱ به نشانی تازه می‌رود",
    )

    class Meta:
        model = Product
        fields = [
            "title", "category", "brand", "short_description", "description",
            "warranty_text", "slug", "seo_title", "seo_description",
        ]
        labels = {
            "title": "عنوان",
            "category": "دسته‌بندی",
            "brand": "برند",
            "short_description": "توضیح کوتاه",
            "description": "توضیحات",
            "warranty_text": "گارانتی",
            "seo_title": "عنوان سئو",
            "seo_description": "توضیحات سئو",
        }
        help_texts = {
            "description": "متن ساده پاراگراف می‌شود. HTML مجاز: p، br، ul، ol، li، strong، em، h2، h3، h4، a، blockquote",
        }
        widgets = {
            "title": FaTextInput(attrs={"class": "input w-full"}),
            "category": forms.Select(attrs={"class": "select w-full"}),
            "brand": forms.Select(attrs={"class": "select w-full"}),
            "short_description": FaTextarea(attrs={"class": "textarea w-full", "rows": 2}),
            "description": forms.Textarea(attrs={"class": "textarea w-full", "rows": 10}),
            "warranty_text": FaTextInput(attrs={"class": "input w-full"}),
            "seo_title": FaTextInput(attrs={"class": "input w-full"}),
            "seo_description": FaTextarea(attrs={"class": "textarea w-full", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        category, brand = self.fields["category"], self.fields["brand"]
        category.queryset = Category.objects.filter(Q(is_active=True) | Q(pk=self.instance.category_id)).order_by("path")
        category.label_from_instance = category_label
        category.empty_label = "انتخاب دسته"
        brand.queryset = Brand.objects.filter(Q(is_active=True) | Q(pk=self.instance.brand_id)).order_by("name_fa")
        brand.empty_label = "بدون برند"

    def clean_title(self) -> str:
        return normalize_fa(self.cleaned_data["title"])

    def clean_short_description(self) -> str:
        return multiline(self.cleaned_data["short_description"])

    def clean_description(self) -> str:
        return rich_text(self.cleaned_data["description"])

    def clean_warranty_text(self) -> str:
        return normalize_fa(self.cleaned_data["warranty_text"])

    def clean_seo_title(self) -> str:
        return normalize_fa(self.cleaned_data["seo_title"])

    def clean_seo_description(self) -> str:
        return multiline(self.cleaned_data["seo_description"])

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 280)


class VariantForm(FieldErrorAttrsMixin, forms.Form):
    title = forms.CharField(label="عنوان تنوع", max_length=200, widget=FaTextInput(attrs={"class": "input w-full"}))
    sku = forms.CharField(
        label="کد کالا (SKU)",
        max_length=64,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr", "autocomplete": "off"}),
    )
    price = TomanField(label="قیمت (تومان)")
    compare_at_price = TomanField(label="قیمت قبل از تخفیف", required=False)
    max_per_order = FaIntegerField(label="حداکثر در هر سفارش", required=False, min_value=0, max_value=999)
    is_active = forms.BooleanField(label="فعال", required=False, widget=forms.CheckboxInput(attrs=CHECKBOX))
    color = forms.CharField(label="رنگ", required=False, max_length=60, widget=FaTextInput(attrs={"class": "input w-full"}))
    model = forms.CharField(label="مدل", required=False, max_length=60, widget=FaTextInput(attrs={"class": "input w-full"}))
    initial_stock = FaIntegerField(label="موجودی اولیه", required=False, min_value=0, max_value=100000)

    def __init__(self, *args, product, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        self.instance = instance
        self.fields["compare_at_price"].widget.attrs["data-discount-from"] = "1"
        if instance is not None:
            del self.fields["initial_stock"]  # stock changes later go through the stock ledger (P12)

    def clean_sku(self) -> str:
        sku = normalize_digits(self.cleaned_data["sku"]).strip()
        if not SKU_RE.match(sku):
            raise ValidationError("کد کالا فقط حرف لاتین، عدد، نقطه، خط تیره و زیرخط دارد")
        clash = Variant.objects.filter(sku=sku)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise ValidationError("این کد کالا برای تنوع دیگری ثبت شده است")
        return sku

    def clean(self):
        cleaned = super().clean()
        price, compare = cleaned.get("price"), cleaned.get("compare_at_price")
        if not compare:
            cleaned["compare_at_price"] = None  # empty or 0 means no discount
        elif price is not None and compare < price:
            self.add_error("compare_at_price", "قیمت قبل از تخفیف نمی‌تواند کمتر از قیمت فروش باشد")
        if not cleaned.get("max_per_order"):
            cleaned["max_per_order"] = None  # empty or 0 means up to the stock (D29)
        return cleaned

    def apply_to(self, variant: Variant) -> None:
        data = self.cleaned_data
        variant.title = normalize_fa(data["title"])
        variant.sku = data["sku"]
        variant.price = data["price"]
        variant.compare_at_price = data["compare_at_price"]
        variant.max_per_order = data["max_per_order"]
        variant.is_active = data["is_active"]
        options = dict(variant.options) if isinstance(variant.options, dict) else {}
        for key in ("color", "model"):  # other option keys are left alone
            value = normalize_fa(data.get(key) or "")
            if value:
                options[key] = value
            else:
                options.pop(key, None)
        variant.options = options


class QuickPriceForm(FieldErrorAttrsMixin, forms.Form):
    """Prices of every variant of one product, edited in the list row."""

    def __init__(self, *args, variants, **kwargs):
        super().__init__(*args, **kwargs)
        self.variants = variants
        for variant in variants:
            self.fields[f"price_{variant.pk}"] = TomanField(label="قیمت", initial=variant.price)
            self.fields[f"compare_{variant.pk}"] = TomanField(
                label="قبل از تخفیف", required=False, initial=variant.compare_at_price
            )

    def clean(self):
        cleaned = super().clean()
        for variant in self.variants:
            price = cleaned.get(f"price_{variant.pk}")
            compare = cleaned.get(f"compare_{variant.pk}") or None
            cleaned[f"compare_{variant.pk}"] = compare
            if compare is not None and price is not None and compare < price:
                self.add_error(f"compare_{variant.pk}", "قیمت قبل از تخفیف نمی‌تواند کمتر از قیمت فروش باشد")
        return cleaned


class SpecNumberField(forms.Field):
    """Persian or Arabic digits, «٬» thousands and «٫» decimals in; a Decimal with two places out."""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        text = _SEPARATORS.sub("", normalize_digits(str(value))).replace("٫", ".")
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValidationError("عدد معتبر وارد کنید") from None
        if not number.is_finite() or abs(number) >= Decimal("1e10"):
            raise ValidationError("عدد بیش از حد بزرگ است")
        return number.quantize(Decimal("0.01"))


class SpecsForm(FieldErrorAttrsMixin, forms.Form):
    """One field per applicable attribute. D41: a number fills both value_number and value_text."""

    def __init__(self, *args, attributes, values=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.attributes = list(attributes)
        existing = values or {}
        for attribute in self.attributes:
            label = f"{attribute.name} ({attribute.unit})" if attribute.unit else attribute.name
            if attribute.type == SpecAttribute.TYPE_BOOL:
                field = forms.ChoiceField(
                    label=label,
                    required=False,
                    choices=[("", "نامشخص"), ("1", "بله"), ("0", "خیر")],
                    widget=forms.Select(attrs={"class": "select w-full"}),
                )
            elif attribute.type == SpecAttribute.TYPE_NUMBER:
                field = SpecNumberField(
                    label=label,
                    required=False,
                    widget=FaDigitsInput(attrs={"class": "input w-full text-end num", "inputmode": "decimal"}),
                )
            else:
                field = forms.CharField(
                    label=label,
                    required=False,
                    max_length=255,
                    widget=FaTextInput(attrs={"class": "input w-full", "list": f"spec-list-{attribute.pk}"}),
                )
            saved = existing.get(attribute.pk)
            if saved is not None:
                if attribute.type == SpecAttribute.TYPE_BOOL:
                    field.initial = "1" if saved.value_number == 1 else "0"
                elif attribute.type == SpecAttribute.TYPE_NUMBER and saved.value_number is not None:
                    field.initial = number_text(saved.value_number)
                else:
                    field.initial = saved.value_text
            self.fields[f"spec_{attribute.pk}"] = field

    def desired(self) -> dict[int, tuple[str, Decimal | None] | None]:
        """attribute id -> (value_text, value_number), or None when the field is empty (the value is removed)."""
        result: dict[int, tuple[str, Decimal | None] | None] = {}
        for attribute in self.attributes:
            value = self.cleaned_data.get(f"spec_{attribute.pk}")
            if attribute.type == SpecAttribute.TYPE_BOOL:
                result[attribute.pk] = (
                    None if value in (None, "") else (("بله", Decimal(1)) if value == "1" else ("خیر", Decimal(0)))
                )
            elif attribute.type == SpecAttribute.TYPE_NUMBER:
                result[attribute.pk] = None if value is None else (number_text(value), value)
            else:
                text = normalize_fa(value or "")
                result[attribute.pk] = (text, None) if text else None
        return result


# --- categories, specification attributes, brands -------------------------------


class CategoryForm(FieldErrorAttrsMixin, forms.ModelForm):
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=180,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
        help_text="خالی = ساخت خودکار از نام",
    )
    featured_order = FaIntegerField(label="ترتیب در دسته‌های برتر", min_value=0, max_value=9999)
    menu_order = FaIntegerField(label="ترتیب در منو", min_value=0, max_value=9999)
    logo_clear = forms.BooleanField(required=False, label="حذف لوگوی فعلی", widget=forms.CheckboxInput(attrs=CHECKBOX))

    class Meta:
        model = Category
        fields = [
            "parent", "name", "slug", "logo", "description", "is_featured", "featured_order",
            "show_in_menu", "menu_order", "is_active", "spec_inherit",
        ]
        labels = {
            "parent": "دسته‌ی والد",
            "name": "نام",
            "logo": "لوگو",
            "description": "توضیح",
            "is_featured": "دسته‌ی برتر",
            "show_in_menu": "نمایش در منو",
            "is_active": "فعال",
            "spec_inherit": "ارث‌بری مشخصات از والد",
        }
        widgets = {
            "parent": forms.Select(attrs={"class": "select w-full"}),
            "name": FaTextInput(attrs={"class": "input w-full"}),
            "logo": forms.FileInput(attrs=FILE_ATTRS),
            "description": FaTextarea(attrs={"class": "textarea w-full", "rows": 3}),
            "is_featured": forms.CheckboxInput(attrs=CHECKBOX),
            "show_in_menu": forms.CheckboxInput(attrs=CHECKBOX),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
            "spec_inherit": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parents = Category.objects.order_by("path")
        if self.instance.pk and self.instance.path:  # a category cannot move under itself or its own subtree
            parents = parents.exclude(
                path__gte=self.instance.path, path__lt=subtree_upper_bound(self.instance.path)
            )
        self.fields["parent"].queryset = parents
        self.fields["parent"].label_from_instance = category_label
        self.fields["parent"].empty_label = "بدون والد (دسته‌ی ریشه)"

    def clean_name(self) -> str:
        return normalize_fa(self.cleaned_data["name"])

    def clean_description(self) -> str:
        return multiline(self.cleaned_data["description"])

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 180)

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if isinstance(logo, UploadedFile):
            validate_upload(logo, max_bytes=LOGO_MAX_BYTES, label="لوگو")
        return logo


class SpecAttributeForm(FieldErrorAttrsMixin, forms.ModelForm):
    sort = FaIntegerField(label="ترتیب", min_value=0, max_value=9999)

    class Meta:
        model = SpecAttribute
        fields = ["name", "type", "unit", "is_filterable", "sort"]
        labels = {"name": "نام", "type": "نوع", "unit": "واحد", "is_filterable": "قابل فیلتر"}
        widgets = {
            "name": FaTextInput(attrs={"class": "input w-full"}),
            "type": forms.Select(attrs={"class": "select w-full"}),
            "unit": FaTextInput(attrs={"class": "input w-full"}),
            "is_filterable": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def clean_name(self) -> str:
        return normalize_fa(self.cleaned_data["name"])

    def clean_unit(self) -> str:
        return normalize_fa(self.cleaned_data["unit"])

    def clean_type(self) -> str:
        new_type = self.cleaned_data["type"]
        if self.instance.pk and new_type != self.instance.type and self.instance.values.exists():
            raise ValidationError("برای مشخصه‌ای که مقدار ثبت‌شده دارد، نوع قابل تغییر نیست")
        return new_type


class BrandForm(FieldErrorAttrsMixin, forms.ModelForm):
    slug = forms.CharField(
        label="نشانی",
        required=False,
        max_length=140,
        widget=forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
        help_text="خالی = ساخت خودکار از نام",
    )
    logo_clear = forms.BooleanField(required=False, label="حذف لوگوی فعلی", widget=forms.CheckboxInput(attrs=CHECKBOX))

    class Meta:
        model = Brand
        fields = ["name_fa", "name_en", "slug", "logo", "aliases", "is_active"]
        labels = {"name_fa": "نام فارسی", "name_en": "نام لاتین", "logo": "لوگو", "is_active": "فعال"}
        widgets = {
            "name_fa": FaTextInput(attrs={"class": "input w-full"}),
            "name_en": forms.TextInput(attrs={"class": "input w-full text-end latin", "dir": "ltr"}),
            "logo": forms.FileInput(attrs=FILE_ATTRS),
            "aliases": FaTextInput(attrs={"class": "input w-full"}),
            "is_active": forms.CheckboxInput(attrs=CHECKBOX),
        }

    def clean_name_fa(self) -> str:
        return normalize_fa(self.cleaned_data["name_fa"])

    def clean_aliases(self) -> str:
        return normalize_fa(self.cleaned_data["aliases"])

    def clean_slug(self) -> str:
        return clean_slug_value(self, self.cleaned_data.get("slug"), 140)

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if isinstance(logo, UploadedFile):
            validate_upload(logo, max_bytes=LOGO_MAX_BYTES, label="لوگو")
        return logo
```

### ۴.۳ `static/js/mm/panel.js` (جایگزین کامل) و `static/js/mm/upload.js` (جدید)

**`panel.js`** (نسخه‌ی V2 + نمایش زنده‌ی مبلغ و درصد تخفیف):

```javascript
/* MM.panel: panel-only behaviour (docs/08-ui-modules.md): toast bridge, copy button, select-all,
   search panel, live money hints. */
(function (MM) {
  "use strict";

  /* HX-Trigger: {"mm:toast": {"message": "...", "level": "success"}} */
  document.addEventListener("mm:toast", function (event) {
    var detail = event.detail || {};
    if (detail.message) MM.ui.toast(detail.message, { level: detail.level || "info" });
  });

  /* ----- money hints: «۱٬۲۵۰٬۰۰۰ تومان» under a [data-toman-hint] field; [data-discount-from] adds the percent ----- */
  function amount(input) {
    var digits = MM.fmt.enDigits(input.value).replace(/[^0-9]/g, "");
    return digits ? parseInt(digits, 10) : 0;
  }
  function grouped(number) {
    return MM.fmt.faDigits(String(number).replace(/\B(?=(\d{3})+(?!\d))/g, "٬"));
  }
  function hint(input) {
    var out = input.parentNode.querySelector("[data-money-out]");
    if (!out) {
      out = document.createElement("p");
      out.setAttribute("data-money-out", "");
      out.className = "text-label text-ink-3 mt-1 min-h-5";
      input.insertAdjacentElement("afterend", out);
    }
    var value = amount(input);
    var text = value ? grouped(value) + " تومان" : "";
    if (value && input.hasAttribute("data-discount-from") && input.form) {
      var price = input.form.querySelector("[name='price']");
      var sale = price ? amount(price) : 0;
      if (sale > 0 && value > sale) {
        text += " — " + MM.fmt.faDigits(Math.round(((value - sale) * 100) / value)) + "٪ تخفیف";
      }
    }
    out.textContent = text;
  }

  document.addEventListener("input", function (event) {
    var el = event.target;
    if (!el.matches || !el.matches("[data-toman-hint]")) return;
    hint(el);
    if (el.name === "price" && el.form) {
      var compare = el.form.querySelector("[data-discount-from]");
      if (compare) hint(compare);
    }
  });

  MM.init("panel-money", function (root) {
    MM.each(root, "[data-toman-hint]", hint);
  });

  /* ----- clicks: copy, select-all, search panel ----- */
  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!target.closest) return;

    var copy = target.closest("[data-copy]");
    if (copy) {
      var source = document.getElementById(copy.getAttribute("data-copy"));
      if (!source || !navigator.clipboard) {
        MM.ui.toast("کپی نشد؛ متن را دستی انتخاب کنید", { level: "error" });
        return;
      }
      navigator.clipboard.writeText(source.value !== undefined ? source.value : source.textContent).then(
        function () { MM.ui.toast("مشخصات کپی شد", { level: "success" }); },
        function () { MM.ui.toast("کپی نشد؛ متن را دستی انتخاب کنید", { level: "error" }); }
      );
      return;
    }

    var all = target.closest("[data-check-all]");
    if (all && all.form) {
      all.form.querySelectorAll("input[name='order']:not(:disabled)").forEach(function (box) { box.checked = all.checked; });
      return;
    }

    var panel = document.getElementById("search-results");
    if (panel && !target.closest("[data-panel-search]")) panel.classList.add("hidden");
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    var swapped = event.detail && event.detail.target;
    if (swapped && swapped.id === "search-results") swapped.classList.toggle("hidden", !swapped.innerHTML.trim());
  });
})(window.MM);
```

**`upload.js`**: فایل‌ها در بسته‌های حداکثر سه‌تایی و نوبتی می‌روند تا هر درخواست از حد nginx (۲۰ مگابایت) پایین بماند. هر بسته یک submit عادی HTMX است:

```javascript
/* MM.upload: drag & drop for a [data-dropzone] form. Files go up in batches of at most 3, one request after
   the other, each as a normal HTMX submit of the zone's form (docs/08-ui-modules.md). */
(function (MM) {
  "use strict";
  var BATCH = 3;
  var queue = [];
  var total = 0;
  var active = null; /* id of the form being fed */

  function zone() { return active ? document.getElementById(active) : null; }

  function progressOf(form) { return form ? form.querySelector("[data-dropzone-progress]") : null; }

  function feed() {
    var form = zone();
    if (!form) { queue = []; active = null; return; }
    var progress = progressOf(form);
    if (progress) {
      progress.max = total;
      progress.value = total - queue.length;
      progress.classList.toggle("hidden", !queue.length);
    }
    if (!queue.length) { active = null; return; }
    var input = form.querySelector("input[type='file']");
    var transfer = new DataTransfer();
    queue.splice(0, BATCH).forEach(function (file) { transfer.items.add(file); });
    input.files = transfer.files;
    window.htmx.trigger(form, "submit");
  }

  function start(form, list) {
    var files = Array.prototype.filter.call(list, function (file) { return file.type.indexOf("image/") === 0; });
    if (files.length !== list.length) MM.ui.toast("فقط فایل تصویری پذیرفته می‌شود", { level: "warning" });
    if (!files.length) return;
    queue = files;
    total = files.length;
    active = form.id;
    feed();
  }

  document.addEventListener("change", function (event) {
    var input = event.target;
    var form = input.closest && input.closest("[data-dropzone]");
    if (form && input.type === "file" && !active) start(form, input.files);
  });

  document.addEventListener("dragover", function (event) {
    var form = event.target.closest && event.target.closest("[data-dropzone]");
    if (!form) return;
    event.preventDefault();
    form.classList.add("bg-base-300");
  });
  document.addEventListener("dragleave", function (event) {
    var form = event.target.closest && event.target.closest("[data-dropzone]");
    if (form) form.classList.remove("bg-base-300");
  });
  document.addEventListener("drop", function (event) {
    var form = event.target.closest && event.target.closest("[data-dropzone]");
    if (!form) return;
    event.preventDefault();
    form.classList.remove("bg-base-300");
    if (!active) start(form, event.dataTransfer.files);
  });

  /* The next batch goes when the gallery section has been swapped in. */
  document.addEventListener("htmx:afterSettle", function (event) {
    if (!active) return;
    var el = event.target;
    if (el && el.closest && el.closest("#sec-gallery")) feed();
  });
  function stop() { queue = []; active = null; }
  document.addEventListener("htmx:responseError", stop);
  document.addEventListener("htmx:sendError", stop);

  MM.upload = { pending: function () { return queue.length; } };
})(window.MM);
```

### ۴.۴ `apps/panel/views/products.py` (جدید)

```python
"""Products in the panel: list, quick price edit and the product studio (docs/09 module 4).

Every write goes through a model save() or a catalog helper, so cache revisions, the FTS row and the
aggregates stay honest. There is no raw .update() on Product, Variant or Category in this module.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog import stock
from apps.catalog.images import validate_upload
from apps.catalog.models import Brand, Category, Product, ProductImage, ProductSpecValue, StockMovement, Variant
from apps.catalog.publishing import publish_checks, sync_main_image
from apps.catalog.specs import applicable_attributes
from apps.catalog.tree import subtree_upper_bound
from apps.core.models import SiteSettings
from apps.core.text import normalize_fa, to_fa_text
from apps.orders.models import OrderItem
from apps.panel import htmx, ordering
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
VIEW = "catalog.view_product"
MAX_IMAGES = 12
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 3 files/batch (upload.js) x 5 MB stays under nginx's 20 MB request limit
STOCK_CHOICES = [("in", "موجود"), ("low", "کم‌موجود"), ("out", "ناموجود")]
SECTIONS = {
    "basics": "panel/products/_sec_basics.html",
    "variants": "panel/products/_sec_variants.html",
    "gallery": "panel/products/_sec_gallery.html",
    "specs": "panel/products/_sec_specs.html",
    "side": "panel/products/_sec_side.html",
}


def _int(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _load(pk: int) -> Product:
    return get_object_or_404(Product.objects.select_related("brand", "category", "main_image"), pk=pk)


# --- list -------------------------------------------------------------------


def _list_context(params, user) -> dict:
    status = params.get("status") if params.get("status") in dict(Product.STATUS_CHOICES) else ""
    stock_filter = params.get("stock") if params.get("stock") in dict(STOCK_CHOICES) else ""
    category = Category.objects.filter(pk=_int(params.get("category"))).first() if params.get("category") else None
    brand_id = _int(params.get("brand"))

    queryset = Product.objects.select_related("brand", "category", "main_image")
    text = normalize_fa(params.get("q", ""), for_search=True)[:80]
    if text:
        queryset = queryset.filter(
            Q(search_text__contains=text) | Q(pk__in=Variant.objects.filter(sku__icontains=text).values("product_id"))
        )
    if category is not None and category.path:
        queryset = queryset.filter(
            category_path__gte=category.path, category_path__lt=subtree_upper_bound(category.path)
        )
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)
    if status:
        queryset = queryset.filter(status=status)
    if stock_filter == "in":
        queryset = queryset.filter(in_stock=True)
    elif stock_filter == "out":
        queryset = queryset.filter(in_stock=False)
    elif stock_filter == "low":
        queryset = queryset.filter(in_stock=True, total_stock__lte=SiteSettings.get_solo().low_stock_threshold)

    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {key: params.get(key, "") for key in ("q", "category", "brand", "status", "stock") if params.get(key)}
    return {
        "page_obj": page_obj,
        "filters": filters,
        "qs": urlencode(filters),
        "hidden": [("page", page_obj.number), *filters.items()],
        "category_choices": [(c.pk, category_label(c)) for c in Category.objects.order_by("path")],
        "brand_choices": list(Brand.objects.order_by("name_fa").values_list("pk", "name_fa")),
        "status_choices": Product.STATUS_CHOICES,
        "stock_choices": STOCK_CHOICES,
        "can_add": user.has_perm("catalog.add_product"),
        "can_quick": user.has_perm("catalog.change_variant"),
        "can_bulk": user.has_perm("catalog.change_product"),
    }


@panel_view(VIEW)
@require_GET
def product_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/products/_list_results.html", context)
    return render(request, "panel/products/list.html", context)


@panel_view(VIEW, "catalog.change_product")
@require_POST
def product_bulk(request):
    """Activate or archive the selected products; activation runs the same checklist as the studio.

    Also doubles as the studio's own publish/archive button (ctx=studio, one product id): that response
    swaps only the side panel instead of the list.
    """
    action = request.POST.get("action")
    ids = [pk for pk in (_int(value) for value in request.POST.getlist("product")[:100]) if pk]
    if action not in ("activate", "archive") or not ids:
        message, level = "محصولی انتخاب نشده است", "error"
    else:
        done, refused = 0, 0
        for product in Product.objects.filter(pk__in=ids):
            target = Product.STATUS_ACTIVE if action == "activate" else Product.STATUS_ARCHIVED
            if target == Product.STATUS_ACTIVE and publish_checks(product)[0]:
                refused += 1
                continue
            if product.status != target:
                product.status = target
                product.save(update_fields=["status", "updated_at"])
                done += 1
        message = to_fa_text(f"{done} محصول تغییر کرد" + (f"، {refused} مورد چک‌لیست انتشار را نگذراند" if refused else ""))
        level = "success" if done and not refused else "warning"

    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:products")
    if request.POST.get("ctx") == "studio" and len(ids) == 1:
        response = render(request, SECTIONS["side"], _studio_context(_load(ids[0]), request.user))
        return htmx.toast(response, message, level)
    response = render(request, "panel/products/_list_results.html", _list_context(request.POST, request.user))
    return htmx.toast(response, message, level)


# --- quick price edit (the list row) ----------------------------------------


def _quick(product, data=None):
    variants = list(product.variants.order_by("sort", "pk"))
    form = QuickPriceForm(data, variants=variants)
    rows = [(v, form[f"price_{v.pk}"], form[f"compare_{v.pk}"]) for v in variants]
    return form, rows


def _row_context(pk, user) -> dict:
    return {
        "p": _load(pk),
        "can_quick": user.has_perm("catalog.change_variant"),
        "can_bulk": user.has_perm("catalog.change_product"),
    }


@panel_view(VIEW, "catalog.change_variant")
@require_http_methods(["GET", "POST"])
def product_quick(request, pk):
    if not request.htmx:
        return redirect("panel:product_studio", pk=pk)
    product = _load(pk)
    form, rows = _quick(product, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        changed = 0
        with transaction.atomic():
            for variant in form.variants:
                price = form.cleaned_data[f"price_{variant.pk}"]
                compare = form.cleaned_data[f"compare_{variant.pk}"]
                if (variant.price, variant.compare_at_price) != (price, compare):
                    variant.price, variant.compare_at_price = price, compare
                    variant.save()
                    changed += 1
        response = render(request, "panel/products/_row.html", _row_context(pk, request.user))
        return htmx.toast(response, "قیمت‌ها ذخیره شد" if changed else "تغییری ثبت نشد")
    return render(request, "panel/products/_row_edit.html", {"p": product, "form": form, "rows": rows})


@panel_view(VIEW)
@require_GET
def product_quick_cancel(request, pk):
    return render(request, "panel/products/_row.html", _row_context(pk, request.user))


# --- create (D39) ------------------------------------------------------------


def suggest_sku(product) -> str:
    base = f"SKU-{product.pk}"
    sku, n = base, 2
    while Variant.objects.filter(sku=sku).exists():
        sku, n = f"{base}-{n}", n + 1
    return sku


@panel_view(VIEW, "catalog.add_product")
@require_http_methods(["GET", "POST"])
def product_new(request):
    form = ProductCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            product = Product.objects.create(
                title=data["title"], category=data["category"], brand=data["brand"], status=Product.STATUS_DRAFT
            )
            Variant.objects.create(product=product, sku=suggest_sku(product), title="پیش‌فرض", price=0, stock=0)
        htmx.flash(request, "پیش‌نویس ساخته شد؛ اطلاعات را کامل کنید")
        return redirect("panel:product_studio", pk=product.pk)
    return render(request, "panel/products/new.html", {"form": form})


# --- studio -------------------------------------------------------------


def _studio_context(product: Product, user) -> dict:
    errors, warnings = publish_checks(product)
    attributes = list(applicable_attributes(product.category)) if product.category_id else []
    values = {v.attribute_id: v for v in product.spec_values.select_related("attribute")}
    return {
        "product": product,
        "basics_form": ProductBasicsForm(instance=product),
        "variants": list(product.variants.order_by("sort", "pk")),
        "images": list(product.images.order_by("sort", "pk")),
        "specs_form": SpecsForm(attributes=attributes, values=values),
        "orphan_values": [v for v in values.values() if v.attribute_id not in {a.pk for a in attributes}],
        "max_images": MAX_IMAGES,
        "errors": errors,
        "warnings": warnings,
        "can_publish": not errors,
        "can_change": user.has_perm("catalog.change_product"),
        "can_variant": user.has_perm("catalog.change_variant"),
        "can_image": user.has_perm("catalog.add_productimage"),
        "can_specs": user.has_perm("catalog.change_productspecvalue"),
        "can_delete": user.has_perm("catalog.delete_product"),
    }


@panel_view(VIEW)
@require_GET
def product_studio(request, pk):
    return render(request, "panel/products/studio.html", _studio_context(_load(pk), request.user))


def _fragments(request, product: Product, primary: str, extra: tuple[str, ...] = ()) -> HttpResponse:
    """Render `primary` as the normal swap target; `extra` and the side panel always ride along out-of-band
    (docs/09 decisions 1-2): the checklist/stats, and a changed category's spec fields, stay in sync everywhere."""
    context = _studio_context(_load(product.pk), request.user)
    html = render(request, SECTIONS[primary], context).content.decode()
    for name in (*extra, "side"):
        html += render(request, SECTIONS[name], {**context, "oob": True}).content.decode()
    return HttpResponse(html)


@panel_view(VIEW, "catalog.change_product")
@require_POST
def product_basics(request, pk):
    product = _load(pk)
    form = ProductBasicsForm(request.POST, instance=product)
    if form.is_valid():
        form.save()  # Product.save() recomputes search_text/category_path and bumps rev/subtree_rev
        return htmx.toast(_fragments(request, product, "basics", extra=("specs",)), "اطلاعات پایه ذخیره شد")
    context = _studio_context(product, request.user)
    context["basics_form"] = form
    return render(request, SECTIONS["basics"], context, status=200)


@panel_view(VIEW, "catalog.delete_product")
@require_POST
def product_delete(request, pk):
    product = _load(pk)
    if product.status != Product.STATUS_DRAFT:
        htmx.flash(request, "فقط محصول پیش‌نویس حذف می‌شود؛ محصول دیگر را بایگانی کنید", "error")
    elif OrderItem.objects.filter(product=product).exists():
        htmx.flash(request, "این محصول در سفارشی استفاده شده است و حذف نمی‌شود", "error")
    elif StockMovement.objects.filter(variant__product=product).exists():
        htmx.flash(request, "این محصول گردش موجودی دارد و حذف نمی‌شود", "error")
    else:
        product.delete()
        htmx.flash(request, "پیش‌نویس حذف شد")
        return redirect("panel:products")
    return redirect("panel:product_studio", pk=pk)


# --- variants ----------------------------------------------------------


@panel_view(VIEW, "catalog.change_variant")
@require_GET
def product_variant_new(request, pk):
    product = _load(pk)
    form = VariantForm(product=product, initial={"is_active": True, "sku": suggest_sku(product)})
    return render(request, "panel/products/_variant_new_form.html", {"product": product, "form": form})


@panel_view(VIEW)
@require_GET
def product_variant_new_cancel(request, pk):
    return HttpResponse("")


@panel_view(VIEW, "catalog.change_variant")
@require_POST
def product_variant_create(request, pk):
    product = _load(pk)
    form = VariantForm(request.POST, product=product)
    if not form.is_valid():
        return render(request, "panel/products/_variant_new_form.html", {"product": product, "form": form})

    with transaction.atomic():
        variant = Variant(product=product, sort=(product.variants.aggregate(Max("sort"))["sort__max"] or -1) + 1)
        form.apply_to(variant)
        variant.save()
        initial_stock = form.cleaned_data.get("initial_stock") or 0
        if initial_stock:
            stock.increment(
                variant.pk, initial_stock, reason=StockMovement.REASON_MANUAL,
                note=f"موجودی اولیه — {request.user.mobile}",
            )
            stock.refresh_products([product.pk])

    context = _studio_context(_load(product.pk), request.user)
    html = "" + render(request, SECTIONS["variants"], {**context, "oob": True}).content.decode()
    html += render(request, SECTIONS["side"], {**context, "oob": True}).content.decode()
    return htmx.toast(HttpResponse(html), "تنوع اضافه شد")


@panel_view(VIEW, "catalog.change_variant")
@require_GET
def product_variant_edit(request, pk, variant_id):
    product = _load(pk)
    variant = get_object_or_404(Variant, pk=variant_id, product=product)
    form = VariantForm(
        product=product, instance=variant,
        initial={
            "title": variant.title, "sku": variant.sku, "price": variant.price,
            "compare_at_price": variant.compare_at_price, "max_per_order": variant.max_per_order,
            "is_active": variant.is_active,
            "color": variant.options.get("color", ""), "model": variant.options.get("model", ""),
        },
    )
    return render(request, "panel/products/_variant_edit_form.html", {"product": product, "form": form, "variant": variant})


@panel_view(VIEW, "catalog.change_variant")
@require_GET
def product_variant_cancel(request, pk, variant_id):
    product = _load(pk)
    variant = get_object_or_404(Variant, pk=variant_id, product=product)
    return render(request, "panel/products/_variant_row.html", {
        "product": product, "variant": variant, "can_variant": request.user.has_perm("catalog.change_variant"),
    })


@panel_view(VIEW, "catalog.change_variant")
@require_POST
def product_variant_update(request, pk, variant_id):
    product = _load(pk)
    variant = get_object_or_404(Variant, pk=variant_id, product=product)
    form = VariantForm(request.POST, product=product, instance=variant)
    if not form.is_valid():
        return render(request, "panel/products/_variant_edit_form.html", {"product": product, "form": form, "variant": variant})

    form.apply_to(variant)
    variant.save()
    context = _studio_context(_load(product.pk), request.user)
    html = render(request, "panel/products/_variant_row.html", {
        "product": product, "variant": Variant.objects.get(pk=variant.pk), "can_variant": context["can_variant"],
    }).content.decode()
    html += render(request, SECTIONS["side"], {**context, "oob": True}).content.decode()
    return htmx.toast(HttpResponse(html), "تنوع ذخیره شد")


@panel_view(VIEW, "catalog.change_variant")
@require_POST
def product_variant_delete(request, pk, variant_id):
    product = _load(pk)
    variant = get_object_or_404(Variant, pk=variant_id, product=product)
    if product.variants.count() <= 1:
        return htmx.toast(_fragments(request, product, "variants"), "محصول باید دست‌کم یک تنوع داشته باشد", "error")
    if variant.stock_movements.exists():
        if variant.is_active:
            variant.is_active = False
            variant.save()  # Variant.save() refreshes aggregates and invalidates the cache
            message = "تنوع دارای گردش موجودی است و فقط غیرفعال شد"
        else:
            message = "این تنوع قبلاً غیرفعال شده است"
    else:
        variant.delete()  # Variant.delete() refreshes aggregates and invalidates the cache
        message = "تنوع حذف شد"
    return htmx.toast(_fragments(request, product, "variants"), message)


@panel_view(VIEW, "catalog.change_variant")
@require_POST
def product_variant_move(request, pk, variant_id):
    product = _load(pk)
    variants = list(product.variants.order_by("sort", "pk"))
    delta = -1 if request.POST.get("dir") == "up" else 1
    moved = ordering.moved(variants, variant_id, delta)
    if moved is not None:
        for variant in ordering.renumber(moved):
            variant.save(update_fields=["sort", "updated_at"])
    return _fragments(request, product, "variants")


# --- gallery (D40) -----------------------------------------------------


@panel_view(VIEW, "catalog.add_productimage")
@require_POST
def product_image_upload(request, pk):
    product = _load(pk)
    room = MAX_IMAGES - product.images.count()
    files = request.FILES.getlist("image")
    if room <= 0:
        return htmx.toast(_fragments(request, product, "gallery"), f"حداکثر {MAX_IMAGES} تصویر مجاز است", "error")

    created, rejected = 0, 0
    with transaction.atomic():
        start = (product.images.aggregate(Max("sort"))["sort__max"] or -1) + 1
        for index, file in enumerate(files[:room]):
            try:
                validate_upload(file, max_bytes=MAX_IMAGE_BYTES, label="تصویر")
            except ValidationError:
                rejected += 1
                continue
            ProductImage.objects.create(product=product, image=file, sort=start + index)
            created += 1
    if created:
        sync_main_image(product)

    overflow = max(0, len(files) - room)
    parts = []
    if created:
        parts.append(f"{created} تصویر اضافه شد")
    if rejected:
        parts.append(f"{rejected} مورد نامعتبر رد شد")
    if overflow:
        parts.append(f"{overflow} مورد به سقف {MAX_IMAGES} تصویر نرسید")
    message = to_fa_text("، ".join(parts) or "تصویری اضافه نشد")
    level = "success" if created and not rejected and not overflow else ("error" if not created else "warning")
    return htmx.toast(_fragments(request, product, "gallery"), message, level)


@panel_view(VIEW, "catalog.delete_productimage")
@require_POST
def product_image_delete(request, pk, image_id):
    product = _load(pk)
    image = get_object_or_404(ProductImage, pk=image_id, product=product)
    if product.main_image_id == image.pk:
        sync_main_image(product, skip_pk=image.pk)  # move the pointer off this image before it's gone
    image.delete()
    return htmx.toast(_fragments(request, product, "gallery"), "تصویر حذف شد")


@panel_view(VIEW, "catalog.change_productimage")
@require_POST
def product_image_move(request, pk, image_id):
    product = _load(pk)
    images = list(product.images.order_by("sort", "pk"))
    delta = -1 if request.POST.get("dir") == "prev" else 1
    moved = ordering.moved(images, image_id, delta)
    if moved is not None:
        for image in ordering.renumber(moved):
            image.save(update_fields=["sort", "updated_at"])
        sync_main_image(product)
    return _fragments(request, product, "gallery")


@panel_view(VIEW, "catalog.change_productimage")
@require_POST
def product_image_front(request, pk, image_id):
    product = _load(pk)
    images = ordering.to_front(list(product.images.order_by("sort", "pk")), image_id)
    for image in ordering.renumber(images):
        image.save(update_fields=["sort", "updated_at"])
    sync_main_image(product)
    return htmx.toast(_fragments(request, product, "gallery"), "تصویر اصلی تغییر کرد")


# --- specs (D41) ---------------------------------------------------------


@panel_view(VIEW, "catalog.change_productspecvalue")
@require_POST
def product_specs(request, pk):
    product = _load(pk)
    attributes = list(applicable_attributes(product.category)) if product.category_id else []
    form = SpecsForm(request.POST, attributes=attributes)
    if not form.is_valid():
        context = _studio_context(product, request.user)
        context["specs_form"] = form
        return render(request, SECTIONS["specs"], context, status=200)

    desired = form.desired()
    existing = {v.attribute_id: v for v in product.spec_values.filter(attribute_id__in=[a.pk for a in attributes])}
    with transaction.atomic():
        for attribute in attributes:
            value = desired[attribute.pk]
            current = existing.get(attribute.pk)
            if value is None:
                if current is not None:
                    current.delete()  # ProductSpecValue.delete() bumps the product's rev (LIST level)
                continue
            text, number = value
            if current is None:
                ProductSpecValue.objects.create(product=product, attribute=attribute, value_text=text, value_number=number)
            elif (current.value_text, current.value_number) != (text, number):
                current.value_text, current.value_number = text, number
                current.save()
    return htmx.toast(_fragments(request, product, "specs"), "مشخصات ذخیره شد")


@panel_view(VIEW, "catalog.change_productspecvalue")
@require_POST
def product_spec_remove(request, pk, value_id):
    product = _load(pk)
    value = get_object_or_404(ProductSpecValue, pk=value_id, product=product)
    value.delete()
    return htmx.toast(_fragments(request, product, "specs"), "مقدار حذف شد")
```

### ۴.۵ `apps/panel/views/categories.py`

```python
"""Categories and their specification attributes in the panel (docs/09 module 5)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.core.jalali import to_fa_digits
from apps.catalog.models import Category, Product, SpecAttribute
from apps.panel import htmx, ordering
from apps.panel.forms_catalog import CategoryForm, SpecAttributeForm
from apps.panel.permissions import panel_view

VIEW = "catalog.view_category"


@panel_view(VIEW)
@require_GET
def category_list(request):
    categories = list(Category.objects.select_related("parent").order_by("path"))
    counts = dict(Product.objects.values_list("category_id").annotate(n=Count("pk")).values_list("category_id", "n"))
    return render(request, "panel/categories/list.html", {
        "categories": categories,
        "counts": counts,
        "can_change": request.user.has_perm("catalog.change_category"),
        "can_add": request.user.has_perm("catalog.add_category"),
    })


@panel_view(VIEW, "catalog.change_category")
@require_http_methods(["GET", "POST"])
def category_form(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category or Category())
        if form.is_valid():
            if form.cleaned_data.get("logo_clear") and not form.cleaned_data.get("logo"):
                form.instance.logo = ""
            form.save()  # Category.save() computes the path and bumps rev/subtree_rev on structural changes
            htmx.flash(request, "دسته‌بندی ذخیره شد")
            return redirect("panel:categories")
    else:
        form = CategoryForm(instance=category)
    attributes = (
        category.spec_attributes.annotate(value_count=Count("values")).order_by("sort", "pk") if category else []
    )
    return render(request, "panel/categories/form.html", {
        "form": form, "category": category, "attributes": attributes,
        "can_add_attribute": request.user.has_perm("catalog.add_specattribute"),
    })


@panel_view(VIEW, "catalog.delete_category")
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.children.exists():
        htmx.flash(request, "دسته‌ای که زیردسته دارد حذف نمی‌شود", "error")
    elif category.products.exists():
        htmx.flash(request, "دسته‌ای که محصول دارد حذف نمی‌شود؛ آن را غیرفعال کنید", "error")
    else:
        category.delete()
        htmx.flash(request, "دسته‌بندی حذف شد")
    return redirect("panel:categories")


@panel_view(VIEW, "catalog.change_category")
@require_POST
def category_move(request, pk):
    """Reorders menu_order among siblings (same parent)."""
    category = get_object_or_404(Category, pk=pk)
    siblings = list(Category.objects.filter(parent=category.parent).order_by("menu_order", "pk"))
    delta = -1 if request.POST.get("dir") == "up" else 1
    moved = ordering.moved(siblings, category.pk, delta)
    if moved is not None:
        with transaction.atomic():
            for sibling in ordering.renumber(moved, field="menu_order"):
                sibling.save(update_fields=["menu_order", "updated_at"])  # a structural field: bumps the menu epoch
    return redirect("panel:categories")


@panel_view(VIEW, "catalog.add_specattribute")
@require_http_methods(["GET", "POST"])
def attribute_form(request, pk, attribute_id=None):
    category = get_object_or_404(Category, pk=pk)
    attribute = get_object_or_404(SpecAttribute, pk=attribute_id, category=category) if attribute_id else None
    if request.method == "POST":
        form = SpecAttributeForm(request.POST, instance=attribute or SpecAttribute(category=category))
        if form.is_valid():
            form.save()  # SpecAttribute.save() invalidates the category's cache
            htmx.flash(request, "مشخصه ذخیره شد")
            return redirect("panel:category_edit", pk=category.pk)
    else:
        form = SpecAttributeForm(instance=attribute)
    return render(request, "panel/categories/attribute_form.html", {"form": form, "category": category, "attribute": attribute})


@panel_view(VIEW, "catalog.delete_specattribute")
@require_POST
def attribute_delete(request, pk, attribute_id):
    category = get_object_or_404(Category, pk=pk)
    attribute = get_object_or_404(SpecAttribute, pk=attribute_id, category=category)
    count = attribute.values.count()
    attribute.delete()  # SpecAttribute.delete() invalidates the category's cache
    message = f"مشخصه حذف شد؛ {to_fa_digits(count)} مقدار محصول هم حذف شد" if count else "مشخصه حذف شد"
    htmx.flash(request, message)
    return redirect("panel:category_edit", pk=category.pk)
```

### ۴.۶ `apps/panel/views/brands.py`

```python
"""Brands in the panel (docs/09 module 6)."""

from __future__ import annotations

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.cache import invalidate_brand
from apps.catalog.models import Brand, Product
from apps.panel import htmx
from apps.panel.forms_catalog import BrandForm
from apps.panel.permissions import panel_view

VIEW = "catalog.view_brand"


@panel_view(VIEW)
@require_GET
def brand_list(request):
    brands = Brand.objects.annotate(
        active_count=Count("products", filter=Q(products__status=Product.STATUS_ACTIVE))
    ).order_by("name_fa")
    return render(request, "panel/brands/list.html", {
        "brands": brands,
        "can_add": request.user.has_perm("catalog.add_brand"),
        "can_change": request.user.has_perm("catalog.change_brand"),
    })


@panel_view(VIEW, "catalog.change_brand")
@require_http_methods(["GET", "POST"])
def brand_form(request, pk=None):
    brand = get_object_or_404(Brand, pk=pk) if pk else None
    if request.method == "POST":
        form = BrandForm(request.POST, request.FILES, instance=brand or Brand())
        if form.is_valid():
            if form.cleaned_data.get("logo_clear") and not form.cleaned_data.get("logo"):
                form.instance.logo = ""
            was_update = brand is not None
            obj = form.save()
            if was_update:
                invalidate_brand(obj.pk)  # name/alias changes affect search_text and list caches of its products
            htmx.flash(request, "برند ذخیره شد")
            return redirect("panel:brands")
    else:
        form = BrandForm(instance=brand)
    return render(request, "panel/brands/form.html", {"form": form, "brand": brand})


@panel_view(VIEW, "catalog.delete_brand")
@require_POST
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if brand.products.exists():
        htmx.flash(request, "برندی که محصول دارد حذف نمی‌شود؛ آن را غیرفعال کنید", "error")
    else:
        brand.delete()
        htmx.flash(request, "برند حذف شد")
    return redirect("panel:brands")
```

### ۴.۷ `apps/panel/urls.py` (جایگزین کامل)

```python
from __future__ import annotations

from django.urls import path

from .views import account, auth, brands, categories, dashboard, orders, payments, products, shell

app_name = "panel"

urlpatterns = [
    path("", dashboard.dashboard, name="dashboard"),
    path("login/", auth.login_view, name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("account/", account.account, name="account"),
    path("account/logout-all/", account.logout_all, name="logout_all"),
    path("search/", shell.search_view, name="search"),
    path("badges/", shell.badges_view, name="badges"),

    path("orders/", orders.order_list, name="orders"),
    path("orders/bulk/", orders.order_bulk, name="order_bulk"),
    path("orders/<str:number>/", orders.order_detail, name="order_detail"),
    path("orders/<str:number>/status/", orders.order_status, name="order_status"),
    path("orders/<str:number>/sms/", orders.order_resend_sms, name="order_resend_sms"),
    path("orders/<str:number>/invoice/", orders.order_invoice, name="order_invoice"),
    path("payments/", payments.payment_list, name="payments"),
    path("payments/<int:pk>/refund/", payments.payment_refund, name="payment_refund"),

    path("products/", products.product_list, name="products"),
    path("products/bulk/", products.product_bulk, name="product_bulk"),
    path("products/new/", products.product_new, name="product_new"),
    path("products/<int:pk>/", products.product_studio, name="product_studio"),
    path("products/<int:pk>/quick/", products.product_quick, name="product_quick"),
    path("products/<int:pk>/quick/cancel/", products.product_quick_cancel, name="product_quick_cancel"),
    path("products/<int:pk>/basics/", products.product_basics, name="product_basics"),
    path("products/<int:pk>/delete/", products.product_delete, name="product_delete"),
    path("products/<int:pk>/variants/new/", products.product_variant_new, name="product_variant_new"),
    path("products/<int:pk>/variants/new/cancel/", products.product_variant_new_cancel, name="product_variant_new_cancel"),
    path("products/<int:pk>/variants/create/", products.product_variant_create, name="product_variant_create"),
    path("products/<int:pk>/variants/<int:variant_id>/edit/", products.product_variant_edit, name="product_variant_edit"),
    path("products/<int:pk>/variants/<int:variant_id>/cancel/", products.product_variant_cancel, name="product_variant_cancel"),
    path("products/<int:pk>/variants/<int:variant_id>/update/", products.product_variant_update, name="product_variant_update"),
    path("products/<int:pk>/variants/<int:variant_id>/delete/", products.product_variant_delete, name="product_variant_delete"),
    path("products/<int:pk>/variants/<int:variant_id>/move/", products.product_variant_move, name="product_variant_move"),
    path("products/<int:pk>/images/upload/", products.product_image_upload, name="product_image_upload"),
    path("products/<int:pk>/images/<int:image_id>/delete/", products.product_image_delete, name="product_image_delete"),
    path("products/<int:pk>/images/<int:image_id>/move/", products.product_image_move, name="product_image_move"),
    path("products/<int:pk>/images/<int:image_id>/front/", products.product_image_front, name="product_image_front"),
    path("products/<int:pk>/specs/", products.product_specs, name="product_specs"),
    path("products/<int:pk>/specs/<int:value_id>/remove/", products.product_spec_remove, name="product_spec_remove"),

    path("categories/", categories.category_list, name="categories"),
    path("categories/new/", categories.category_form, name="category_new"),
    path("categories/<int:pk>/", categories.category_form, name="category_edit"),
    path("categories/<int:pk>/delete/", categories.category_delete, name="category_delete"),
    path("categories/<int:pk>/move/", categories.category_move, name="category_move"),
    path("categories/<int:pk>/attributes/new/", categories.attribute_form, name="attribute_new"),
    path("categories/<int:pk>/attributes/<int:attribute_id>/", categories.attribute_form, name="attribute_edit"),
    path("categories/<int:pk>/attributes/<int:attribute_id>/delete/", categories.attribute_delete, name="attribute_delete"),

    path("brands/", brands.brand_list, name="brands"),
    path("brands/new/", brands.brand_form, name="brand_new"),
    path("brands/<int:pk>/", brands.brand_form, name="brand_edit"),
    path("brands/<int:pk>/delete/", brands.brand_delete, name="brand_delete"),
]
```

---

## ۵. قالب‌ها

مسیر `templates/panel/products/`، `templates/panel/categories/`، `templates/panel/brands/`.

### `panel/products/list.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}محصولات{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="محصولات" %}
    <div class="flex items-center gap-2">
      <span id="products-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
      {% if can_add %}<a href="{% url 'panel:product_new' %}" class="btn btn-primary h-10 min-h-10">محصول تازه</a>{% endif %}
    </div>
  </div>

  <form action="{% url 'panel:products' %}" method="get" role="search"
        hx-get="{% url 'panel:products' %}" hx-target="#products-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-indicator="#products-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3">
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ filters.q }}" placeholder="عنوان یا کد کالا" class="grow text-small" autocomplete="off">
    </label>
    <select name="category" class="select h-10 w-44 text-small">
      <option value="">همه‌ی دسته‌ها</option>
      {% for id, label in category_choices %}<option value="{{ id }}" {% if filters.category == id|stringformat:"s" %}selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <select name="brand" class="select h-10 w-36 text-small">
      <option value="">همه‌ی برندها</option>
      {% for id, name in brand_choices %}<option value="{{ id }}" {% if filters.brand == id|stringformat:"s" %}selected{% endif %}>{{ name }}</option>{% endfor %}
    </select>
    <select name="status" class="select h-10 w-32 text-small">
      <option value="">همه‌ی وضعیت‌ها</option>
      {% for value, label in status_choices %}<option value="{{ value }}" {% if filters.status == value %}selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <select name="stock" class="select h-10 w-32 text-small">
      <option value="">همه‌ی موجودی‌ها</option>
      {% for value, label in stock_choices %}<option value="{{ value }}" {% if filters.stock == value %}selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
  </form>

  <div id="products-results" aria-live="polite">{% include "panel/products/_list_results.html" %}</div>
</div>
{% endblock %}
```

### `panel/products/_list_results.html`
```html
{% load core_tags %}
<form method="post" action="{% url 'panel:product_bulk' %}" hx-post="{% url 'panel:product_bulk' %}"
      hx-target="#products-results" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']">
  {% csrf_token %}
  {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
  <div class="bg-base-100 border rounded-box overflow-x-auto">
    <table class="table table-sm">
      <thead><tr>
        {% if can_bulk %}<th scope="col" class="w-10"><input type="checkbox" data-check-all class="checkbox checkbox-sm" aria-label="انتخاب همه"></th>{% endif %}
        <th scope="col"></th><th scope="col">عنوان</th><th scope="col">برند</th><th scope="col">دسته</th>
        <th scope="col">قیمت (تومان)</th><th scope="col">موجودی</th><th scope="col">وضعیت</th><th scope="col"></th>
      </tr></thead>
      <tbody>
        {% for p in page_obj.object_list %}{% include "panel/products/_row.html" with p=p can_quick=can_quick can_bulk=can_bulk %}{% endfor %}
      </tbody>
    </table>
  </div>
  {% if can_bulk and page_obj.object_list %}
    <div class="flex items-center gap-2 mt-3">
      <button type="submit" name="action" value="activate" class="btn btn-sm h-10 bg-base-300 border">فعال‌سازی انتخاب‌شده‌ها</button>
      <button type="submit" name="action" value="archive" class="btn btn-sm h-10 bg-base-300 border">بایگانی انتخاب‌شده‌ها</button>
    </div>
  {% endif %}
</form>
{% if not page_obj.object_list %}{% include "partials/_empty_state.html" with title="محصولی پیدا نشد" description="فیلترها را تغییر دهید" %}{% endif %}
{% include "panel/partials/_pagination.html" with target="#products-results" %}
```

### `panel/products/_row.html`
```html
{% load core_tags panel_tags %}
<tr id="product-row-{{ p.pk }}">
  {% if can_bulk %}<td><input type="checkbox" name="product" value="{{ p.pk }}" class="checkbox checkbox-sm"{% if p.status != "draft" and p.status != "archived" %} disabled{% endif %}></td>{% endif %}
  <td><span class="w-10 h-10 rounded bg-white border overflow-hidden flex items-center justify-center">
    {% if p.main_image %}<img src="{{ p.main_image|thumb_url }}" alt="" width="40" height="40" class="w-full h-full object-contain">{% else %}{% icon "image" size=16 class="text-ink-3" %}{% endif %}
  </span></td>
  <td><a href="{% url 'panel:product_studio' p.pk %}" class="link link-hover">{{ p.title|fa_text }}</a></td>
  <td>{{ p.brand.name_fa|default:"—"|fa_text }}</td>
  <td>{{ p.category.name|fa_text }}</td>
  <td class="whitespace-nowrap">{{ p.min_price|toman }}</td>
  <td>{{ p.total_stock|fa_digits }}</td>
  <td><span class="flex items-center gap-2 text-small whitespace-nowrap"><span class="status {{ p.status|product_dot }}"></span>{{ p.get_status_display }}</span></td>
  <td>{% if can_quick %}<button type="button" class="btn btn-ghost btn-xs" hx-get="{% url 'panel:product_quick' p.pk %}" hx-target="#product-row-{{ p.pk }}" hx-swap="outerHTML">ویرایش سریع قیمت</button>{% endif %}</td>
</tr>
```

### `panel/products/_row_edit.html`
```html
{% load core_tags %}
<tr id="product-row-{{ p.pk }}">
  <td colspan="8">
    <form hx-post="{% url 'panel:product_quick' p.pk %}" hx-target="#product-row-{{ p.pk }}" hx-swap="outerHTML"
          hx-disabled-elt="find button[type='submit']" class="flex flex-wrap items-end gap-3 py-2">
      {% csrf_token %}
      {% for variant, price_field, compare_field in rows %}
        <div class="flex flex-col gap-1">
          <span class="text-label text-ink-3">{{ variant.title|fa_text }}</span>
          <div class="flex items-center gap-2">{{ price_field }}{{ compare_field }}</div>
        </div>
      {% endfor %}
      <div class="flex items-center gap-2">
        <button type="submit" class="btn btn-primary btn-sm h-9">ذخیره</button>
        <button type="button" class="btn btn-ghost btn-sm h-9" hx-get="{% url 'panel:product_quick_cancel' p.pk %}" hx-target="#product-row-{{ p.pk }}" hx-swap="outerHTML">انصراف</button>
      </div>
    </form>
  </td>
</tr>
```

### `panel/products/new.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}محصول تازه{% endblock %}
{% block content %}
<div class="max-w-lg mx-auto flex flex-col gap-4">
  {% include "panel/partials/_page_heading.html" with title="محصول تازه" %}
  <form method="post" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for field in form %}
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
        {{ field }}
        {% for error in field.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 %}<span>{{ error }}</span></p>{% endfor %}
      </fieldset>
    {% endfor %}
    <button type="submit" class="btn btn-primary h-11 min-h-11">ساخت پیش‌نویس و رفتن به استودیو</button>
  </form>
</div>
{% endblock %}
```

### `panel/products/studio.html`
```html
{% extends "panel/shell.html" %}
{% load static core_tags %}
{% block title %}{{ product.title|fa_text }}{% endblock %}
{% block content %}
<div class="flex items-center gap-3 mb-4">
  <a href="{% url 'panel:products' %}" class="btn btn-ghost btn-square w-10 h-10" aria-label="بازگشت">{% icon "arrow-left" size=18 flip=True %}</a>
  {% include "panel/partials/_page_heading.html" with title=product.title|default:"محصول تازه" %}
  <a href="{{ product.get_absolute_url }}" target="_blank" rel="noopener" class="btn btn-ghost h-10 text-small ms-auto">مشاهده در فروشگاه</a>
</div>
<div class="lg:grid lg:grid-cols-[1fr_320px] lg:gap-6 items-start flex flex-col gap-4">
  <div class="flex flex-col gap-4 min-w-0">
    {% include "panel/products/_sec_basics.html" %}
    {% include "panel/products/_sec_variants.html" %}
    {% include "panel/products/_sec_gallery.html" %}
    {% include "panel/products/_sec_specs.html" %}
  </div>
  {% include "panel/products/_sec_side.html" %}
</div>
{% endblock %}
{% block extra_js %}<script src="{% static 'js/mm/upload.js' %}" defer></script>{% endblock %}
```

### `panel/products/_sec_basics.html`
```html
{% load core_tags %}
<section id="sec-basics" {% if oob %}hx-swap-oob="true"{% endif %} class="bg-base-100 border rounded-box p-4 flex flex-col gap-4">
  <h2 class="text-lead font-medium">اطلاعات پایه</h2>
  <form hx-post="{% url 'panel:product_basics' product.pk %}" hx-target="#sec-basics" hx-swap="outerHTML"
        hx-disabled-elt="find button[type='submit']" hx-indicator="#basics-indicator" novalidate class="flex flex-col gap-4">
    {% csrf_token %}
    {% if basics_form.non_field_errors %}<div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 %}{% for e in basics_form.non_field_errors %}<span>{{ e }}</span>{% endfor %}</div>{% endif %}
    {% for field in basics_form %}
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
        {{ field }}
        {% if field.help_text %}<p class="label text-label text-ink-3">{{ field.help_text }}</p>{% endif %}
        {% for error in field.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 %}<span>{{ error }}</span></p>{% endfor %}
      </fieldset>
    {% endfor %}
    <div class="border-t pt-4">
      <button type="submit" class="btn btn-primary h-10 min-h-10" {% if not can_change %}disabled{% endif %}>
        ذخیره<span id="basics-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
      </button>
    </div>
  </form>
</section>
```

### `panel/products/_sec_variants.html`
```html
{% load core_tags %}
<section id="sec-variants" {% if oob %}hx-swap-oob="true"{% endif %} class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
  <div class="flex items-center justify-between gap-2">
    <h2 class="text-lead font-medium">تنوع و قیمت</h2>
    {% if can_variant %}<button type="button" class="btn btn-sm h-9 bg-base-300 border" hx-get="{% url 'panel:product_variant_new' product.pk %}" hx-target="#variant-new-slot" hx-swap="innerHTML">افزودن تنوع</button>{% endif %}
  </div>
  <div id="variant-new-slot"></div>
  <div class="overflow-x-auto">
    <table class="table table-sm">
      <thead><tr><th>عنوان</th><th>SKU</th><th>قیمت</th><th>قبل از تخفیف</th><th>حداکثر سفارش</th><th>فعال</th><th></th></tr></thead>
      <tbody>{% for variant in variants %}{% include "panel/products/_variant_row.html" %}{% endfor %}</tbody>
    </table>
  </div>
</section>
```

### `panel/products/_variant_row.html`
```html
{% load core_tags %}
<tr id="variant-row-{{ variant.pk }}">
  <td>{{ variant.title|fa_text }}</td>
  <td class="latin">{{ variant.sku }}</td>
  <td class="whitespace-nowrap">{{ variant.price|toman }}</td>
  <td class="whitespace-nowrap">{% if variant.compare_at_price %}{{ variant.compare_at_price|toman }}{% else %}—{% endif %}</td>
  <td>{{ variant.max_per_order|default:"—"|fa_digits }}</td>
  <td>{% if variant.is_active %}{% icon "check" size=16 class="text-success" %}{% else %}—{% endif %}</td>
  <td class="flex items-center gap-1 flex-wrap">
    {% if can_variant %}
      <button type="button" class="btn btn-ghost btn-xs" hx-post="{% url 'panel:product_variant_move' product.pk variant.pk %}" hx-vals='{"dir":"up"}' hx-target="#sec-variants" hx-swap="outerHTML">{% icon "chevron-up" size=14 %}</button>
      <button type="button" class="btn btn-ghost btn-xs" hx-post="{% url 'panel:product_variant_move' product.pk variant.pk %}" hx-vals='{"dir":"down"}' hx-target="#sec-variants" hx-swap="outerHTML">{% icon "chevron-down" size=14 %}</button>
      <button type="button" class="btn btn-ghost btn-xs" hx-get="{% url 'panel:product_variant_edit' product.pk variant.pk %}" hx-target="#variant-row-{{ variant.pk }}" hx-swap="outerHTML">ویرایش</button>
      <button type="button" class="btn btn-ghost btn-xs text-error" hx-post="{% url 'panel:product_variant_delete' product.pk variant.pk %}" hx-target="#sec-variants" hx-swap="outerHTML" data-confirm="این تنوع حذف یا (در صورت داشتن گردش موجودی) غیرفعال شود؟">حذف</button>
    {% endif %}
  </td>
</tr>
```

### `panel/products/_variant_new_form.html`
```html
{% load core_tags %}
<form hx-post="{% url 'panel:product_variant_create' product.pk %}" hx-target="#variant-new-slot" hx-swap="innerHTML"
      hx-disabled-elt="find button[type='submit']" class="bg-base-200 rounded-field p-3 flex flex-wrap items-end gap-3" novalidate>
  {% csrf_token %}
  {% for field in form %}
    <fieldset class="fieldset">
      <legend class="fieldset-legend text-label text-ink-3">{{ field.label }}</legend>
      {{ field }}
      {% for error in field.errors %}<p class="text-label text-error">{{ error }}</p>{% endfor %}
    </fieldset>
  {% endfor %}
  <div class="flex items-center gap-2">
    <button type="submit" class="btn btn-primary btn-sm h-9">افزودن</button>
    <button type="button" class="btn btn-ghost btn-sm h-9" hx-get="{% url 'panel:product_variant_new_cancel' product.pk %}" hx-target="#variant-new-slot" hx-swap="innerHTML">انصراف</button>
  </div>
</form>
```

**نکته‌ی مهم:** `hx-target` این فرم `#variant-new-slot` است، نه `#sec-variants`. موفقیت (`product_variant_create`) پاسخی می‌دهد که خودش محتوای این اسلات را خالی می‌کند (رشته‌ی خالی برای تارگت) و جدول را با OOB تازه می‌کند؛ شکست فقط همین فرم را با خطا دوباره در همین اسلات می‌نشاند.

### `panel/products/_variant_edit_form.html`
```html
{% load core_tags %}
<tr id="variant-row-{{ variant.pk }}">
  <td colspan="7">
    <form hx-post="{% url 'panel:product_variant_update' product.pk variant.pk %}" hx-target="#variant-row-{{ variant.pk }}" hx-swap="outerHTML"
          hx-disabled-elt="find button[type='submit']" class="flex flex-wrap items-end gap-3 py-2" novalidate>
      {% csrf_token %}
      {% for field in form %}
        <fieldset class="fieldset">
          <legend class="fieldset-legend text-label text-ink-3">{{ field.label }}</legend>
          {{ field }}
          {% for error in field.errors %}<p class="text-label text-error">{{ error }}</p>{% endfor %}
        </fieldset>
      {% endfor %}
      <div class="flex items-center gap-2">
        <button type="submit" class="btn btn-primary btn-sm h-9">ذخیره</button>
        <button type="button" class="btn btn-ghost btn-sm h-9" hx-get="{% url 'panel:product_variant_cancel' product.pk variant.pk %}" hx-target="#variant-row-{{ variant.pk }}" hx-swap="outerHTML">انصراف</button>
      </div>
    </form>
  </td>
</tr>
```

### `panel/products/_sec_gallery.html`
```html
{% load core_tags %}
<section id="sec-gallery" {% if oob %}hx-swap-oob="true"{% endif %} class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
  <div class="flex items-center justify-between gap-2">
    <h2 class="text-lead font-medium">گالری تصاویر</h2>
    <span class="text-label text-ink-3">{{ images|length|fa_digits }} از {{ max_images|fa_digits }}</span>
  </div>

  {% if can_image %}
    <form id="gallery-dropzone" data-dropzone hx-post="{% url 'panel:product_image_upload' product.pk %}"
          hx-target="#sec-gallery" hx-swap="outerHTML" hx-encoding="multipart/form-data"
          class="border-2 border-dashed rounded-field p-6 flex flex-col items-center gap-2 text-center transition-colors">
      {% csrf_token %}
      {% icon "upload" size=24 class="text-ink-3" %}
      <p class="text-small text-ink-2">تصاویر را بکشید و رها کنید، یا</p>
      <label class="btn btn-sm h-9 bg-base-300 border cursor-pointer">انتخاب فایل
        <input type="file" name="image" accept="image/png,image/jpeg,image/webp" multiple class="hidden">
      </label>
      <progress data-dropzone-progress class="progress progress-primary w-full hidden" value="0" max="1"></progress>
    </form>
  {% endif %}

  {% if images %}
    <div class="flex gap-3 overflow-x-auto no-scrollbar">
      {% for image in images %}
        <div class="relative shrink-0 w-28">
          <span class="block w-28 h-28 rounded-lg bg-white border overflow-hidden">
            <img src="{{ image|thumb_url }}" alt="" width="112" height="112" class="w-full h-full object-contain">
          </span>
          {% if forloop.first %}<span class="badge badge-sm bg-base-content text-base-100 border-0 absolute top-1 start-1">اصلی</span>{% endif %}
          {% if can_image %}
            <div class="flex items-center justify-center gap-1 mt-1 flex-wrap">
              <button type="button" class="btn btn-ghost btn-xs" hx-post="{% url 'panel:product_image_move' product.pk image.pk %}" hx-vals='{"dir":"prev"}' hx-target="#sec-gallery" hx-swap="outerHTML">{% icon "chevron-right" size=14 flip=True %}</button>
              {% if not forloop.first %}<button type="button" class="btn btn-ghost btn-xs" hx-post="{% url 'panel:product_image_front' product.pk image.pk %}" hx-target="#sec-gallery" hx-swap="outerHTML">اصلی</button>{% endif %}
              <button type="button" class="btn btn-ghost btn-xs" hx-post="{% url 'panel:product_image_move' product.pk image.pk %}" hx-vals='{"dir":"next"}' hx-target="#sec-gallery" hx-swap="outerHTML">{% icon "chevron-left" size=14 flip=True %}</button>
              <button type="button" class="btn btn-ghost btn-xs text-error" hx-post="{% url 'panel:product_image_delete' product.pk image.pk %}" hx-target="#sec-gallery" hx-swap="outerHTML" data-confirm="این تصویر حذف شود؟" data-confirm-tone="danger">حذف</button>
            </div>
          {% endif %}
        </div>
      {% endfor %}
    </div>
  {% else %}
    <p class="text-small text-ink-2">هنوز تصویری اضافه نشده است</p>
  {% endif %}
</section>
```

### `panel/products/_sec_specs.html`
```html
{% load core_tags %}
<section id="sec-specs" {% if oob %}hx-swap-oob="true"{% endif %} class="bg-base-100 border rounded-box p-4 flex flex-col gap-4">
  <h2 class="text-lead font-medium">مشخصات فنی</h2>
  {% if specs_form.fields %}
    <form hx-post="{% url 'panel:product_specs' product.pk %}" hx-target="#sec-specs" hx-swap="outerHTML"
          hx-disabled-elt="find button[type='submit']" class="grid sm:grid-cols-2 gap-4" novalidate>
      {% csrf_token %}
      {% for field in specs_form %}
        <fieldset class="fieldset">
          <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
          {{ field }}
          {% for error in field.errors %}<p class="text-label text-error">{{ error }}</p>{% endfor %}
        </fieldset>
      {% endfor %}
      <div class="sm:col-span-2 border-t pt-4">
        <button type="submit" class="btn btn-primary h-10 min-h-10" {% if not can_specs %}disabled{% endif %}>ذخیره مشخصات</button>
      </div>
    </form>
  {% else %}
    <p class="text-small text-ink-2">برای دسته‌ی این محصول مشخصه‌ای تعریف نشده است</p>
  {% endif %}

  {% if orphan_values %}
    <div class="border-t pt-4 flex flex-col gap-2">
      <span class="text-label text-ink-3">خارج از دسته‌ی فعلی</span>
      {% for value in orphan_values %}
        <div class="flex items-center justify-between gap-2 text-small">
          <span>{{ value.attribute.name|fa_text }}: {{ value.value_text|default:value.value_number|fa_text }}</span>
          <button type="button" class="btn btn-ghost btn-xs text-error" hx-post="{% url 'panel:product_spec_remove' product.pk value.pk %}" hx-target="#sec-specs" hx-swap="outerHTML">حذف</button>
        </div>
      {% endfor %}
    </div>
  {% endif %}
</section>
```

### `panel/products/_sec_side.html`
```html
{% load core_tags panel_tags %}
<aside id="sec-side" {% if oob %}hx-swap-oob="true"{% endif %} class="bg-base-100 border rounded-box p-4 flex flex-col gap-4 w-full lg:sticky lg:top-20">
  <span class="flex items-center gap-2 text-small"><span class="status {{ product.status|product_dot }}"></span>{{ product.get_status_display }}</span>

  {% if errors %}<div role="alert" class="alert alert-error text-small flex-col items-start gap-1">{% for error in errors %}<span class="flex items-center gap-2">{% icon "alert-circle" size=16 class="shrink-0" %}{{ error }}</span>{% endfor %}</div>{% endif %}
  {% if warnings %}<div role="alert" class="alert text-small flex-col items-start gap-1">{% for warning in warnings %}<span class="flex items-center gap-2">{% icon "info" size=16 class="shrink-0" %}{{ warning }}</span>{% endfor %}</div>{% endif %}

  {% if can_change %}
    <div class="border-t pt-4">
      {% if product.status != "active" %}
        <form hx-post="{% url 'panel:product_bulk' %}" hx-target="#sec-side" hx-swap="outerHTML">
          {% csrf_token %}<input type="hidden" name="action" value="activate"><input type="hidden" name="product" value="{{ product.pk }}"><input type="hidden" name="ctx" value="studio">
          <button type="submit" class="btn btn-primary w-full h-10 min-h-10" {% if not can_publish %}disabled{% endif %}>تایید و انتشار</button>
        </form>
      {% else %}
        <form hx-post="{% url 'panel:product_bulk' %}" hx-target="#sec-side" hx-swap="outerHTML">
          {% csrf_token %}<input type="hidden" name="action" value="archive"><input type="hidden" name="product" value="{{ product.pk }}"><input type="hidden" name="ctx" value="studio">
          <button type="submit" class="btn bg-base-300 border w-full h-10 min-h-10">بایگانی</button>
        </form>
      {% endif %}
    </div>
  {% endif %}

  <div class="flex flex-col gap-1 text-small text-ink-2 border-t pt-4">
    <span>لایک: {{ product.like_count|fa_digits }}</span>
    <span>امتیاز: {{ product.rating_avg|fa_digits }} ({{ product.review_count|fa_digits }} نظر)</span>
    <span>خرید ۳۰ روز: {{ product.purchase_count_30d|fa_digits }}</span>
  </div>

  {% if can_delete and product.status == "draft" %}
    <form method="post" action="{% url 'panel:product_delete' product.pk %}" class="border-t pt-4" data-confirm="این پیش‌نویس برای همیشه حذف شود؟" data-confirm-tone="danger">
      {% csrf_token %}
      <button type="submit" class="btn btn-ghost w-full h-10 text-error">حذف پیش‌نویس</button>
    </form>
  {% endif %}
</aside>
```

### `panel/categories/list.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags catalog_tags %}
{% block title %}دسته‌بندی‌ها{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="دسته‌بندی‌ها" %}
    {% if can_add %}<a href="{% url 'panel:category_new' %}" class="btn btn-primary h-10 min-h-10">دسته‌ی تازه</a>{% endif %}
  </div>
  <div class="bg-base-100 border rounded-box overflow-x-auto">
    <table class="table table-sm">
      <thead><tr><th>نام</th><th>تعداد محصول</th><th>برتر</th><th>در منو</th><th>فعال</th><th></th></tr></thead>
      <tbody>
        {% for category in categories %}
          <tr>
            <td><span style="padding-inline-start: {{ category.depth }}rem" class="inline-block">{{ category.name|fa_text }}</span></td>
            <td>{{ counts|get_item:category.pk|default:0|fa_digits }}</td>
            <td>{% if category.is_featured %}{% icon "check" size=16 class="text-success" %}{% endif %}</td>
            <td>{% if category.show_in_menu %}{% icon "check" size=16 class="text-success" %}{% endif %}</td>
            <td>{% if category.is_active %}{% icon "check" size=16 class="text-success" %}{% else %}—{% endif %}</td>
            <td class="flex items-center gap-1">
              {% if can_change %}
                <form method="post" action="{% url 'panel:category_move' category.pk %}" class="inline-flex"><input type="hidden" name="dir" value="up">{% csrf_token %}<button class="btn btn-ghost btn-xs">{% icon "chevron-up" size=14 %}</button></form>
                <form method="post" action="{% url 'panel:category_move' category.pk %}" class="inline-flex"><input type="hidden" name="dir" value="down">{% csrf_token %}<button class="btn btn-ghost btn-xs">{% icon "chevron-down" size=14 %}</button></form>
                <a href="{% url 'panel:category_edit' category.pk %}" class="btn btn-ghost btn-xs">ویرایش</a>
              {% endif %}
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

### `panel/categories/form.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}{% if category %}ویرایش دسته{% else %}دسته‌ی تازه{% endif %}{% endblock %}
{% block content %}
<div class="max-w-2xl flex flex-col gap-6">
  {% include "panel/partials/_page_heading.html" with title=category.name|default:"دسته‌ی تازه" %}
  <form method="post" enctype="multipart/form-data" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for field in form %}
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
        {{ field }}
        {% if field.help_text %}<p class="label text-label text-ink-3">{{ field.help_text }}</p>{% endif %}
        {% for error in field.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 %}<span>{{ error }}</span></p>{% endfor %}
      </fieldset>
    {% endfor %}
    <div class="flex items-center gap-2 border-t pt-4">
      <button type="submit" class="btn btn-primary h-11 min-h-11">ذخیره</button>
      <a href="{% url 'panel:categories' %}" class="btn btn-ghost h-11 text-ink-2">انصراف</a>
    </div>
  </form>

  {% if category %}
    <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-lead font-medium">مشخصات فنی این دسته</h2>
        {% if can_add_attribute %}<a href="{% url 'panel:attribute_new' category.pk %}" class="btn btn-sm h-9 bg-base-300 border">مشخصه‌ی تازه</a>{% endif %}
      </div>
      <div class="overflow-x-auto">
        <table class="table table-sm">
          <thead><tr><th>نام</th><th>نوع</th><th>واحد</th><th>قابل فیلتر</th><th>مقدار ثبت‌شده</th><th></th></tr></thead>
          <tbody>
            {% for attribute in attributes %}
              <tr>
                <td>{{ attribute.name|fa_text }}</td>
                <td>{{ attribute.get_type_display }}</td>
                <td>{{ attribute.unit|fa_text }}</td>
                <td>{% if attribute.is_filterable %}{% icon "check" size=16 class="text-success" %}{% endif %}</td>
                <td>{{ attribute.value_count|fa_digits }}</td>
                <td class="flex items-center gap-2">
                  <a href="{% url 'panel:attribute_edit' category.pk attribute.pk %}" class="btn btn-ghost btn-xs">ویرایش</a>
                  <form method="post" action="{% url 'panel:attribute_delete' category.pk attribute.pk %}"
                        data-confirm="{% if attribute.value_count %}این مشخصه {{ attribute.value_count|fa_digits }} مقدار محصول دارد که با آن حذف می‌شود. حذف شود؟{% else %}این مشخصه حذف شود؟{% endif %}" data-confirm-tone="danger">
                    {% csrf_token %}<button type="submit" class="btn btn-ghost btn-xs text-error">حذف</button>
                  </form>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>
  {% endif %}
</div>
{% endblock %}
```

### `panel/categories/attribute_form.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}مشخصه‌ی فنی{% endblock %}
{% block content %}
<div class="max-w-md flex flex-col gap-4">
  {% include "panel/partials/_page_heading.html" with title="مشخصه‌ی فنی" %}
  <form method="post" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for field in form %}
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
        {{ field }}
        {% for error in field.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 %}<span>{{ error }}</span></p>{% endfor %}
      </fieldset>
    {% endfor %}
    <div class="flex items-center gap-2 border-t pt-4">
      <button type="submit" class="btn btn-primary h-11 min-h-11">ذخیره</button>
      <a href="{% url 'panel:category_edit' category.pk %}" class="btn btn-ghost h-11 text-ink-2">انصراف</a>
    </div>
  </form>
</div>
{% endblock %}
```

### `panel/brands/list.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}برندها{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="برندها" %}
    {% if can_add %}<a href="{% url 'panel:brand_new' %}" class="btn btn-primary h-10 min-h-10">برند تازه</a>{% endif %}
  </div>
  <div class="bg-base-100 border rounded-box overflow-x-auto">
    <table class="table table-sm">
      <thead><tr><th></th><th>نام</th><th>تعداد محصول فعال</th><th>فعال</th><th></th></tr></thead>
      <tbody>
        {% for brand in brands %}
          <tr>
            <td><span class="w-8 h-8 rounded bg-white border overflow-hidden flex items-center justify-center">{% if brand.logo %}<img src="{{ brand.logo.url }}" alt="" width="32" height="32" class="w-full h-full object-contain">{% else %}{% icon "tag" size=14 class="text-ink-3" %}{% endif %}</span></td>
            <td>{{ brand.name_fa|fa_text }}</td>
            <td>{{ brand.active_count|fa_digits }}</td>
            <td>{% if brand.is_active %}{% icon "check" size=16 class="text-success" %}{% else %}—{% endif %}</td>
            <td>{% if can_change %}<a href="{% url 'panel:brand_edit' brand.pk %}" class="btn btn-ghost btn-xs">ویرایش</a>{% endif %}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

### `panel/brands/form.html`
```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}برند{% endblock %}
{% block content %}
<div class="max-w-lg flex flex-col gap-4">
  {% include "panel/partials/_page_heading.html" with title=brand.name_fa|default:"برند تازه" %}
  <form method="post" enctype="multipart/form-data" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for field in form %}
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
        {{ field }}
        {% if field.help_text %}<p class="label text-label text-ink-3">{{ field.help_text }}</p>{% endif %}
        {% for error in field.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 %}<span>{{ error }}</span></p>{% endfor %}
      </fieldset>
    {% endfor %}
    <div class="flex items-center gap-2 border-t pt-4">
      <button type="submit" class="btn btn-primary h-11 min-h-11">ذخیره</button>
      <a href="{% url 'panel:brands' %}" class="btn btn-ghost h-11 text-ink-2">انصراف</a>
    </div>
  </form>
  {% if brand %}
    <form method="post" action="{% url 'panel:brand_delete' brand.pk %}" data-confirm="این برند حذف شود؟" data-confirm-tone="danger">
      {% csrf_token %}<button type="submit" class="btn btn-ghost h-10 text-error">حذف برند</button>
    </form>
  {% endif %}
</div>
{% endblock %}
```

---

## ۶. تست‌ها — `apps/panel/tests/test_catalog.py`

فقط پول/موجودی/مجوز/امنیت/باطل‌سازی کش. از `staff_client` و فیکسچرهای ریشه (`product`, `child_category`, `brand`) استفاده می‌کند.

```python
"""Panel catalog: publishing rules, stock on create, image ordering, specs (docs/09 modules 4-6)."""

from __future__ import annotations

import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalog.models import Brand, Category, Product, ProductSpecValue, SpecAttribute, StockMovement, Variant
from apps.catalog.publishing import publish_checks

pytestmark = pytest.mark.django_db


def _png(name="a.png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/png")


def test_publish_checks_block_activation_without_price(product):
    Variant.objects.filter(product=product).update(price=0)
    errors, _ = publish_checks(Product.objects.get(pk=product.pk))
    assert any("قیمت" in e for e in errors)


def test_bulk_activate_refuses_products_that_fail_the_checklist(staff_client, child_category):
    draft = Product.objects.create(title="بدون قیمت", category=child_category, status=Product.STATUS_DRAFT)
    Variant.objects.create(product=draft, sku="NOPRICE-1", price=0, stock=0)
    client = staff_client("catalog.view_product", "catalog.change_product")

    client.post("/panel/products/bulk/", {"action": "activate", "product": [draft.pk]})

    draft.refresh_from_db()
    assert draft.status == Product.STATUS_DRAFT


def test_creating_a_variant_with_initial_stock_logs_a_movement_and_refreshes_aggregates(staff_client, product):
    client = staff_client("catalog.view_product", "catalog.change_variant")

    client.post(
        f"/panel/products/{product.pk}/variants/create/",
        {"title": "مشکی", "sku": "WM-1234-BLK", "price": 50_000_000, "is_active": "on", "initial_stock": "3"},
    )

    variant = Variant.objects.get(sku="WM-1234-BLK")
    assert variant.stock == 3
    assert StockMovement.objects.filter(variant=variant, reason=StockMovement.REASON_MANUAL, delta=3).exists()
    assert Product.objects.get(pk=product.pk).total_stock == 8  # 5 from the fixture variant + 3 new


def test_a_variant_with_stock_history_is_deactivated_not_deleted(staff_client, product):
    variant = product.variants.get()
    StockMovement.objects.create(variant=variant, delta=-1, reason=StockMovement.REASON_ORDER)
    Variant.objects.create(product=product, sku="SPARE-1", price=1, stock=0)
    client = staff_client("catalog.view_product", "catalog.change_variant")

    client.post(f"/panel/products/{product.pk}/variants/{variant.pk}/delete/")

    variant.refresh_from_db()
    assert variant.is_active is False
    assert Variant.objects.filter(pk=variant.pk).exists()


def test_sku_must_be_unique_across_variants(staff_client, product):
    existing_sku = product.variants.get().sku
    client = staff_client("catalog.view_product", "catalog.change_variant")

    response = client.post(
        f"/panel/products/{product.pk}/variants/create/",
        {"title": "تکراری", "sku": existing_sku, "price": 1, "is_active": "on"},
    )

    assert "قبلاً" in response.content.decode()
    assert product.variants.count() == 1


def test_the_first_image_by_order_is_always_the_main_image(staff_client, product):
    client = staff_client(
        "catalog.view_product", "catalog.add_productimage", "catalog.change_productimage", "catalog.delete_productimage"
    )
    client.post(f"/panel/products/{product.pk}/images/upload/", {"image": [_png("a.png"), _png("b.png")]})
    product.refresh_from_db()
    first = product.images.order_by("sort", "pk").first()
    assert product.main_image_id == first.pk

    client.post(f"/panel/products/{product.pk}/images/{first.pk}/delete/")

    product.refresh_from_db()
    second = product.images.order_by("sort", "pk").first()
    assert product.main_image_id == second.pk


def test_a_numeric_spec_value_fills_both_text_and_number(staff_client, product, child_category):
    attribute = SpecAttribute.objects.create(category=child_category, name="وزن", type=SpecAttribute.TYPE_NUMBER, unit="kg")
    client = staff_client("catalog.view_product", "catalog.change_productspecvalue")

    client.post(f"/panel/products/{product.pk}/specs/", {f"spec_{attribute.pk}": "۹٫۵"})

    value = ProductSpecValue.objects.get(product=product, attribute=attribute)
    assert value.value_text == "9.5"
    assert value.value_number == Decimal("9.50")


def test_changing_a_spec_attribute_type_is_refused_once_it_has_values(staff_client, product, child_category):
    attribute = SpecAttribute.objects.create(category=child_category, name="رنگ", type=SpecAttribute.TYPE_TEXT)
    ProductSpecValue.objects.create(product=product, attribute=attribute, value_text="سفید")
    client = staff_client("catalog.view_category", "catalog.add_specattribute")

    client.post(
        f"/panel/categories/{child_category.pk}/attributes/{attribute.pk}/",
        {"name": "رنگ", "type": SpecAttribute.TYPE_NUMBER, "unit": "", "sort": "0"},
    )

    attribute.refresh_from_db()
    assert attribute.type == SpecAttribute.TYPE_TEXT


def test_a_category_with_products_cannot_be_deleted(staff_client, child_category, product):
    client = staff_client("catalog.view_category", "catalog.delete_category")
    client.post(f"/panel/categories/{child_category.pk}/delete/")
    assert Category.objects.filter(pk=child_category.pk).exists()


def test_a_brand_with_products_cannot_be_deleted(staff_client, brand, product):
    client = staff_client("catalog.view_brand", "catalog.delete_brand")
    client.post(f"/panel/brands/{brand.pk}/delete/")
    assert Brand.objects.filter(pk=brand.pk).exists()


def test_editing_a_brand_name_updates_products_search_text(staff_client, brand, product):
    client = staff_client("catalog.view_brand", "catalog.change_brand")

    client.post(f"/panel/brands/{brand.pk}/", {
        "name_fa": "برند تازه", "name_en": brand.name_en, "aliases": brand.aliases, "is_active": "on",
    })

    product.refresh_from_db()
    assert "برند تازه" in product.search_text
```

(تست متای `test_every_panel_view_declares_its_access_rule` در `apps/panel/tests/test_access.py` از فاز P10 خودکار همه‌ی URLهای تازه را هم می‌سنجد؛ تکرار لازم نیست.)

---

## ۷. اسناد

- `docs/09-panel-spec.md`: تصمیم‌های بخش ۲ این بریف (۱ تا ۹) را زیر ماژول‌های ۴ تا ۶ ثبت کن. D46 را **به `[DECIDED موقت]`** تغییر بده: «textarea با sanitize؛ تصمیم نهایی بعد از پاسخ کاربر در پایان P11».
- `docs/03-data-model.md`: چیزی عوض نشده (بدون مدل/مهاجرت تازه)؛ فقط اگر `sync_main_image`/`publish_checks` به‌عنوان مسیر نوشتن رسمی جایی ارجاع داده می‌شود اشاره کن.
- `docs/phases/STATUS.md`: ردیف P10 را «تمام‌شده (با ترمیم در P11)» و ردیف P11 را با خلاصه‌ی این فاز پر کن؛ در بخش یادداشت‌ها نقص‌های بخش ۰ و رفعشان را یک‌خطی بنویس.

---

## ۸. سوال برای کاربر (در پایان فاز بپرس، منتظر نمان)

> «توضیحات محصول فعلاً textarea ساده است (متن با Enter پاراگراف می‌شود). چون من نمی‌توانم RTL و ارقام فارسی یک ویرایشگر گرافیکی را در مرورگر ببینم و بسنجم، تصمیم درباره‌ی افزودن ویرایشگر متن غنی (مثل Trix) با شماست. می‌خواهید در فاز جداگانه اضافه شود؟»

اگر پاسخ منفی بود یا نیامد: D46 در `docs/09` به `[DECIDED]` نهایی تبدیل شود (textarea ساده). اگر مثبت بود: فاز جدا تعریف شود، نه ادامه‌ی همین فاز.

---

## ۹. Definition of Done

- [ ] بخش ۰ (ترمیم P10) سبز است: `check`، `pytest`، `ruff check` بدون خطا — **قبل از شروع بقیه**.
- [ ] هیچ `update()` خام روی `Product`/`Variant`/`Category`/`Brand` در `apps/panel/` نیست (تست معماری `test_architecture.py` این را خودکار می‌سنجد).
- [ ] تصویر موبایلیِ دارای EXIF چرخیده دیگر کج رندر نمی‌شود (`ImageOps.exif_transpose`).
- [ ] `sync_main_image` بعد از آپلود، حذف و جابه‌جایی همیشه اولین تصویر را `main_image` می‌کند (D40).
- [ ] تنوع دارای `StockMovement` هرگز حذف نمی‌شود، فقط غیرفعال.
- [ ] موجودی اولیه‌ی تنوع تازه یک ردیف `StockMovement(reason="manual")` می‌سازد و aggregateهای محصول را درست نگه می‌دارد.
- [ ] مقدار عددی مشخصه هم `value_text` و هم `value_number` را پر می‌کند (D41).
- [ ] تغییر نوع مشخصه‌ی دارای مقدار رد می‌شود.
- [ ] حذف دسته/برند دارای محصول رد می‌شود؛ حذف محصول فقط برای پیش‌نویس دست‌نخورده کار می‌کند.
- [ ] سوال D46 (بخش ۸) پرسیده شده و جوابش (یا نبودش) در `docs/09` ثبت شده است.

### مشترک همه‌ی فازهای پنل
- [ ] `uv run pytest` و `uv run ruff check .` و `uv run ruff format .` بدون خطا.
- [ ] grepهای `04` بخش ۱۳ روی `templates/` (شامل `templates/panel/`) و `static/src/` صفر نتیجه می‌دهند.
- [ ] `pnpm run build:css` اجرا شده و `static/css/app.css` commit شده است.
- [ ] `uv run python scripts/build_sprite.py` اجرا شده و هیچ آیکونی ناموجود نیست (آیکون‌های تازه: `package`, `layout-grid`, `tag`, `upload`, `chevron-up`, `chevron-down`).
- [ ] اسناد `09` و `STATUS.md` به‌روز است.

---

## ۱۰. بررسی چشمی (فقط با شما؛ من مرورگر یا Playwright اجرا نمی‌کنم)

- فهرست محصولات: فیلترها کار می‌کنند؛ ویرایش سریع قیمت یک ردیف را فرم می‌کند و «ذخیره»/«انصراف» برمی‌گردانند؛ فعال/بایگانی دسته‌جمعی toast می‌دهد.
- ساخت محصول تازه → ورود به استودیو.
- استودیو/پایه: تغییر دسته باعث عوض‌شدن فیلدهای بخش مشخصات می‌شود؛ ذخیره toast می‌دهد.
- استودیو/تنوع: افزودن با موجودی اولیه کار می‌کند؛ ویرایش درون‌خطی یک ردیف؛ ↑↓ ترتیب؛ حذف تنوعِ بدون گردش واقعاً حذف می‌شود، حذف تنوع دارای گردش فقط غیرفعالش می‌کند؛ پیام تایید (confirm) قبل از حذف ظاهر می‌شود.
- استودیو/گالری: drag&drop و انتخاب فایل هر دو کار می‌کنند؛ اولین تصویر «اصلی» دارد؛ جابه‌جایی/اصلی‌کردن/حذف درست کار می‌کنند؛ فایل غیرتصویری رد می‌شود با پیام فارسی.
- استودیو/مشخصات: فیلدهای دسته نشان داده می‌شوند؛ رقم فارسی و ممیز فارسی (٫) در فیلد عددی پذیرفته می‌شود؛ بعد از تغییر دسته، مقدار قدیمی زیر «خارج از دسته‌ی فعلی» با گزینه‌ی حذف می‌آید.
- ستون کناری: خطا/هشدار درست است؛ دکمه‌ی «تایید و انتشار» بدون رفع خطا غیرفعال/مسدود است.
- دسته‌ها: ساخت/ویرایش، ↑↓ ترتیب، تب مشخصات (افزودن/ویرایش/حذف با پیام تعداد مقدار وابسته)، حذف دسته‌ی دارای محصول یا زیردسته رد می‌شود.
- برندها: ساخت/ویرایش با لوگو، حذف برند دارای محصول رد می‌شود.
- مجوز: کاربر «محتوا» همه را می‌بیند؛ کاربر بی‌مجوز کاتالوگ به `/panel/products/` وارد نمی‌شود (۴۰۳).
- دو تم و عرض‌های ۳۲۰ و ۱۲۸۰: بدون اسکرول افقی ناخواسته، ارقام فارسی همه‌جا.

---

## جواب سوال جدا: کامیت فاز P10

بله، همین حالا کامیت کن — ولی بعد از اینکه بخش ۰ این بریف (ترمیم‌ها) را اعمال کردی و `check`/`pytest`/`ruff` سبز شد، نه قبلش. دلیلش:

1. قاعده‌ی خود پروژه این است که هر فاز در یک نشست جداست؛ این فقط وقتی معنا دارد که مرز بین فازها در گیت هم مشخص باشد. اگر ترمیم P10 را commit نشده روی سرت نگه داری و مستقیم بریف P11 را شروع کنی، هر خطای تازه در P11 قاطی خطاهای باقی‌مانده‌ی P10 می‌شود و تشخیص اینکه کدام تغییر چیز را خراب کرده سخت می‌شود — دقیقاً همان مشکلی که در گزارش آخر پیش آمد.
2. یک نقطه‌ی برگشت تمیز داری: اگر P11 به مشکل خورد، `git reset` به همین کامیت می‌برد به حالت P10 واقعاً کارکن، نه به یک حالت نامعلوم وسط راه.
3. پیام کامیت را دقیق بنویس، مثلاً: `fix: restore shipping helpers, panel templates and P10 tests (phase 10 remediation)` — تا بعداً اگر چیزی دوباره خراب شد، از دیف همین کامیت بفهمی دقیقاً چه چیزی درست شد.

اگر remote داری (گیت‌هاب و غیره)، push هم بزن؛ برای بک‌آپ ضرری ندارد و اگر بین نشست‌ها از ماشین دیگری هم ادامه بدهی لازم می‌شود. اگر فقط لوکال کار می‌کنی، commit به‌تنهایی کافی است و push فوریتی ندارد.
