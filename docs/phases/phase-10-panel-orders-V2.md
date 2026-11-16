# فاز P10 — سفارش‌ها، پرداخت‌ها و بازگشت وجه

> این بریف جایگزین `docs/phases/phase-10-panel-orders.md` می‌شود.
> **هدف:** کارمند فروش کل کار روزانه‌ی سفارش را از `/panel/` انجام دهد: آماده‌سازی، ثبت ارسال با کد رهگیری، تحویل، لغو، بازگشت وجه، فاکتور، پیامک.
> بازگشت وجه هم از ادمین و هم از پنل فقط از یک سرویس (`payments.services.record_refund`) می‌گذرد (D42).

## ۱. وضعیت ورودی: نقص‌های P9 که اول باید درست شود

کدی که از P9 تحویل شده در این موارد شکسته است. تا اصلاح نشود پروژه یا اجرا نمی‌شود یا پنل در مرورگر کار نمی‌کند:

| فایل | نقص |
|---|---|
| `apps/core/seo.py` | `PRIVATE_PATHS` شامل `` `n `` (نشت PowerShell) است: SyntaxError و کل پروژه import نمی‌شود |
| `scripts/build_sprite.py` | `NAV_ICON_RE` قبل از `import re` تعریف شده (NameError) و تورفتگی خط `names.update(...)` غلط است |
| `check_launch.py` | پیام خطای `ADMIN_URL` به `?????` تبدیل شده |
| `views/dashboard.py`، `views/account.py` | `@panel_view` روی متد کلاس گذاشته شده؛ دکوراتور تابع‌محور است و `self` را به‌جای `request` می‌گیرد |
| `views/auth.py` | ورود با HTMX بعد از موفقیت یک redirect معمولی می‌دهد و صفحه‌ی داشبورد داخل فرم می‌نشیند. حلقه‌ی ریدایرکت بی‌نهایت هم هست: staff که با نشست ادمین وارد است ولی `panel_login_at` ندارد، از ورود به داشبورد و از داشبورد به ورود می‌رود |
| `templates/panel/*` | `base.html` سینتکس Jinja دارد (`{{ static(...) }}`)؛ `dashboard.html` خودش را extend می‌کند؛ `403.html`، `account.html`، `badge.html`، `search_results.html` نیستند؛ `sidebar.html` لود تگ ندارد؛ htmx و CSRF header در base پنل نیست |
| `templates/partials/_mm_dialog.html` | خالی است و دیالوگ هنوز داخل `base.html` فروشگاه است |
| `static/js/mm/panel.js` | از `alert()` استفاده می‌کند (D31؛ `test_ui_rules` رد می‌کند) |
| `views/shell.py` | `badges_view` JSON می‌دهد ولی هیچ مصرف‌کننده‌ای ندارد |
| `tests/test_architecture/test_imports.py` | به cwd وابسته است و import بی‌مصرف دارد |

## ۲. مطالعه

`docs/09` ماژول‌های ۱، ۲، ۳، ۱۵ و بخش ۲.۴ تا ۲.۷، `docs/10` کامل، `docs/04` بخش ۴.۱ و ۹.۴ و ۱۳، `docs/08`، `docs/06` فقط بخش ۵ و ۶.

کد: `apps/orders/{workflow,services,notify,shipping,invoice,admin}.py`، `apps/payments/{services,admin,models}.py`، `apps/panel/*`، `apps/accounts/management/commands/setup_groups.py`، `apps/core/{jalali_forms,jalali,testing,cache}.py`، `conftest.py` ریشه.

اسکیل‌ها: `htmx-patterns`، `daisyui` (drawer، table، tabs، steps، modal با popover، alert)، `unslop` چک‌لیست انتها.

## ۳. سوال از کاربر (`[OPEN]`، قبل از رسیدن به آن بخش، بدون توقف بقیه‌ی کار)

> «چاپ دسته‌جمعی فاکتور (چند سفارش انتخاب‌شده در یک صفحه‌ی چاپ) در P10 ساخته شود یا فعلاً فقط چاپ تک‌سفارش؟»

اگر جواب نداد: **ساخته نشود**، و تصمیم در `docs/09` بخش ۲.۱۰ مورد ۵ ثبت شود.

## ۴. تصمیم‌های فاز (همه `[ASSUMPTION]`، در `docs/09` ثبت شوند)

1. `record_refund` تنها راه `REFUNDED` شدن یک `Payment` است. فرم تغییر وضعیت ادمین گزینه‌ی «بازگشت وجه» را ندارد.
2. تعریف «پرداخت تکراری» در `refund_candidates`: وجود پرداخت قبلی با وضعیت `VERIFIED` **یا** `REFUNDED`. وگرنه با بسته شدن پرداخت اول، پرداخت دوم بی‌صدا از گزارش می‌افتد.
3. تغییر وضعیت سفارش ردِ خودش را در `OrderStatusLog` دارد و در `LogEntry` تکرار نمی‌شود. فقط بازگشت وجه و ارسال دوباره‌ی پیامک `audit.log` می‌گیرند. `audit` از `apps.panel` است، پس سرویس دامنه آن را صدا نمی‌زند و فراخواننده (view یا ادمین) ثبت می‌کند.
4. لینک نقشه فعلاً OpenStreetMap است. اگر `docs/vendors/neshan/` لینک اشتراک‌گذاری مستند داشت، همان را بگذار (`[VERIFY]`).
5. ارسال دوباره‌ی پیامک: حداکثر ۳ بار در ساعت برای هر سفارش (هزینه‌ی پیامک).
6. «شروع آماده‌سازی» در داشبورد از همان endpoint دسته‌جمعی (`order_bulk` با `ctx=dashboard`) رد می‌شود.

## ۵. کارها (به همین ترتیب)

### ۵.۰ ترمیم P9

**۵.۰.۱ `apps/core/seo.py`** (فقط `PRIVATE_PATHS`):

```python
PRIVATE_PATHS = (
    "/account/",
    "/auth/",
    "/panel/",
    "/login/",
    "/cart/",
    "/checkout/",
    "/orders/",
    "/payments/",
    "/geo/",
    "/likes/",
    "/social/",
    "/reviews/",
    "/similar/",
    "/search/suggest/",
    "/p/*/variant/",
    "/r/",
    "/_styleguide/",
)
```

**۵.۰.۲ `scripts/build_sprite.py`:** خط اول (`NAV_ICON_RE = ...`) را حذف کن و بعد از `ICON_RE` اضافه کن:

```python
ICON_RE = re.compile(r"""\{%\s*icon\s+["']([a-z0-9-]+)["']""")
NAV_ICON_RE = re.compile(r"""\bicon\s*=\s*["']([a-z0-9-]+)["']""")  # NavItem(icon="...") in apps/panel
```

و حلقه‌ی اسکن را با تورفتگی درست بنویس:

```python
                text = path.read_text(encoding="utf-8", errors="ignore")
                names.update(ICON_RE.findall(text))
                if path.suffix == ".py" and "panel" in path.parts:
                    names.update(NAV_ICON_RE.findall(text))
```

**۵.۰.۳ `check_launch.py`:**

```python
    if settings.ADMIN_URL.startswith("panel/"):
        yield ERROR, "ADMIN_URL نباید با panel/ شروع شود (با مسیر پنل تداخل دارد)"
```

**۵.۰.۴ دیالوگ مشترک:** بلوک `<dialog id="mm-dialog">...</dialog>` را از `templates/base.html` ببر داخل `templates/partials/_mm_dialog.html` (بدون تغییر محتوا) و در `base.html` فروشگاه جایش `{% include "partials/_mm_dialog.html" %}` بگذار.

**۵.۰.۵ `apps/panel/apps.py`:**

```python
class PanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.panel"
    verbose_name = "پنل مدیریت"

    def ready(self) -> None:
        from apps.panel import providers  # noqa: F401  (registers search providers and nav badges)
```

**۵.۰.۶ `apps/panel/htmx.py`:**

```python
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import render
from django_htmx.http import trigger_client_event

LEVELS = {"success": messages.SUCCESS, "error": messages.ERROR, "warning": messages.WARNING, "info": messages.INFO}


def toast(response, message: str, level: str = "success"):
    return trigger_client_event(response, "mm:toast", {"message": message, "level": level})


def flash(request, message: str, level: str = "success") -> None:
    """The same message for a request without HTMX (shown by the base template)."""
    messages.add_message(request, LEVELS.get(level, messages.INFO), message)


def page_or_partial(request, page: str, partial: str, context: dict, **kwargs):
    return render(request, partial if request.htmx else page, context, **kwargs)
```

**۵.۰.۷ `apps/panel/forms.py`** (فرم‌های مرده‌ی `PanelLoginForm` و `SearchForm` حذف می‌شوند):

```python
"""Panel forms."""

from __future__ import annotations

import re

from django import forms

from apps.core.jalali import to_fa_digits
from apps.core.text import normalize_digits
from apps.orders import workflow
from apps.orders.models import Order

TRACKING_RE = re.compile(r"^[0-9A-Za-z-]*$")
STAFF_TARGETS = (Order.PROCESSING, Order.SHIPPED, Order.DELIVERED, Order.CANCELLED)


class PasswordChangeForm(forms.Form):
    old = forms.CharField(label="رمز فعلی", widget=forms.PasswordInput(attrs={"class": "input w-full"}))
    new1 = forms.CharField(label="رمز جدید", widget=forms.PasswordInput(attrs={"class": "input w-full"}))
    new2 = forms.CharField(label="تکرار رمز جدید", widget=forms.PasswordInput(attrs={"class": "input w-full"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new1") != cleaned.get("new2"):
            self.add_error("new2", "رمزها مطابقت ندارند")
        return cleaned


class StatusChangeForm(forms.Form):
    """Input of one staff move. Whether the move is allowed is decided by workflow.change_status, not here."""

    to = forms.ChoiceField(
        choices=[(code, code) for code in STAFF_TARGETS],
        error_messages={"required": "وضعیت جدید را مشخص کنید", "invalid_choice": "تغییر وضعیت نامعتبر است"},
    )
    tracking_code = forms.CharField(required=False)
    note = forms.CharField(
        required=False, max_length=200, error_messages={"max_length": "یادداشت حداکثر ۲۰۰ نویسه است"}
    )

    def clean_tracking_code(self) -> str:
        code = normalize_digits(self.cleaned_data["tracking_code"]).strip()
        if len(code) > workflow.MAX_TRACKING_LENGTH:
            raise forms.ValidationError(f"کد رهگیری حداکثر {to_fa_digits(workflow.MAX_TRACKING_LENGTH)} نویسه است")
        if not TRACKING_RE.match(code):
            raise forms.ValidationError("کد رهگیری فقط حرف لاتین، عدد و خط تیره دارد")
        return code

    def clean_note(self) -> str:
        return " ".join(self.cleaned_data["note"].split())

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("to") == Order.CANCELLED and not cleaned.get("note"):
            self.add_error("note", "برای لغو سفارش، دلیل را بنویسید")
        return cleaned

    def first_error(self) -> str:
        for errors in self.errors.values():
            return str(errors[0])
        return ""
```

**۵.۰.۸ `apps/panel/views/auth.py`** (جایگزین کامل؛ `login_form.html` حذف شود):

```python
from __future__ import annotations

from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.panel import auth
from apps.panel.permissions import public_view


@public_view
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.method == "GET":
        # Only a *panel* session skips the form: an admin-only session has no panel_login_at and would loop.
        if request.user.is_authenticated and request.user.is_staff and auth.session_state(request) == auth.STATE_OK:
            return redirect(auth.safe_next(request, request.GET.get("next")))
        return render(request, "panel/login.html", {"next": request.GET.get("next", "")})

    mobile = request.POST.get("mobile", "")
    next_url = request.POST.get("next", "")
    outcome = auth.try_login(request, mobile, request.POST.get("password", ""))
    if outcome == auth.OK:
        return redirect(auth.safe_next(request, next_url))
    error = auth.LOGIN_FAILED if outcome == auth.INVALID else auth.LOGIN_THROTTLED
    return render(request, "panel/login.html", {"next": next_url, "mobile": mobile, "error": error})


@public_view
@require_POST
def logout_view(request):
    logout(request)
    return redirect("panel:login")
```

**۵.۰.۹ `apps/panel/views/account.py`** (جایگزین کامل؛ شامل «خروج از همه‌ی دستگاه‌ها» از `09` بخش ۲.۴):

```python
from __future__ import annotations

from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import F
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts.models import User
from apps.panel import audit, htmx
from apps.panel.forms import PasswordChangeForm
from apps.panel.permissions import panel_view


@panel_view(authenticated_only=True)
@require_http_methods(["GET", "POST"])
def account(request):
    form = PasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, new = request.user, form.cleaned_data["new1"]
        if not user.check_password(form.cleaned_data["old"]):
            form.add_error("old", "رمز فعلی درست نیست")
        else:
            try:
                validate_password(new, user)
            except ValidationError as exc:
                form.add_error("new1", exc)
            else:
                user.set_password(new)
                user.session_version += 1  # every other session ends; this one is kept below
                user.save(update_fields=["password", "session_version"])
                update_session_auth_hash(request, user)
                audit.log(user, user, audit.CHANGE, "تغییر رمز عبور")
                htmx.flash(request, "رمز تغییر کرد")
                return redirect("panel:account")
    return render(request, "panel/account.html", {"form": form})


@panel_view(authenticated_only=True)
@require_POST
def logout_all(request):
    User.objects.filter(pk=request.user.pk).update(session_version=F("session_version") + 1)
    logout(request)
    return redirect("panel:login")
```

**۵.۰.۱۰ `apps/panel/views/shell.py`:**

```python
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.text import normalize_fa
from apps.panel import badges, nav, search
from apps.panel.permissions import panel_view


@panel_view(authenticated_only=True)
@require_GET
def search_view(request):
    query = request.GET.get("q", "")
    if len(normalize_fa(query)) < search.MIN_LENGTH:
        return HttpResponse("")
    return render(request, "panel/partials/search_results.html", {"results": search.search(request.user, query)})


@panel_view(authenticated_only=True)
@require_GET
def badges_view(request):
    """The sidebar again, polled every 60 s: fresh counters, active link from the page the poll came from."""
    path = (request.htmx.current_url_abs_path if request.htmx else "") or ""
    context = {
        "groups": nav.visible_groups(request.user, path),
        "counts": badges.counts_for(request.user),
        "request": request,
    }
    return render(request, "panel/partials/sidebar.html", context)
```

**۵.۰.۱۱ `apps/panel/templatetags/panel_tags.py`** (پارامتر `oob` برای به‌روزرسانی بج‌ها بعد از تغییر وضعیت):

```python
from __future__ import annotations

from django import template

from apps.panel import badges, nav
from apps.payments.models import Payment

register = template.Library()

PAYMENT_DOT = {Payment.VERIFIED: "status-success", Payment.VERIFYING: "status-info", Payment.FAILED: "status-error"}


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
```

**۵.۰.۱۲ `apps/panel/tests/test_architecture/test_imports.py`:**

```python
"""D35: only apps/panel may import apps.panel."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
IMPORT = re.compile(r"^\s*(from\s+apps\.panel|import\s+apps\.panel)", re.M)


def test_only_the_panel_imports_the_panel():
    offenders = [
        str(path.relative_to(ROOT))
        for folder in ("apps", "config", "scripts")
        for path in (ROOT / folder).rglob("*.py")
        if "apps/panel/" not in path.as_posix() and IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders
```

### ۵.۱ منطق دامنه

**۵.۱.۱ `apps/payments/services.py`:** import جدید، تعریف بازگشت وجه، و اصلاح `refund_candidates`.

```python
from apps.orders import workflow  # next to the other apps.orders imports
```

```python
class RefundError(Exception):
    """A refusal whose message is safe to show to staff."""


@dataclass(frozen=True)
class RefundResult:
    payment: Payment
    order_refunded: bool


def record_refund(payment_id: int, *, by, note: str) -> RefundResult:
    """The only road from a verified payment to «refunded» (D42); admin and panel both call it.

    Staff return the money in the gateway panel first; this records that it happened. The order moves first,
    because workflow.allowed_targets needs the VERIFIED payment to still be there. Callers write the audit entry.
    """
    note = " ".join((note or "").split())[:200]
    if not note:
        raise RefundError("یادداشت لازم است (مثلاً شماره‌ی پیگیری بازگشت وجه)")
    with transaction.atomic():
        payment = Payment.objects.select_related("order").filter(pk=payment_id).first()
        if payment is None:
            raise RefundError("پرداخت پیدا نشد")
        if payment.status == Payment.REFUNDED:
            raise RefundError("بازگشت وجه این پرداخت قبلاً ثبت شده است")
        if payment.status != Payment.VERIFIED:
            raise RefundError("فقط پرداخت تاییدشده بازگشت وجه می‌خورد")

        order = payment.order
        duplicate = Payment.objects.filter(
            order_id=order.pk, status__in=[Payment.VERIFIED, Payment.REFUNDED], pk__lt=payment.pk
        ).exists()
        order_refunded = False
        if not duplicate and order.status in (Order.CANCELLED, Order.EXPIRED, Order.DELIVERED):
            try:
                workflow.change_status(order.pk, Order.REFUNDED, by=by, note=note)
            except workflow.TransitionError as exc:
                raise RefundError(str(exc)) from exc
            order_refunded = True
        elif not duplicate and order.status != Order.REFUNDED:
            raise RefundError("سفارش هنوز در جریان است؛ لغو یا تحویل آن را ثبت کنید")

        if not _move(payment.pk, [Payment.VERIFIED], status=Payment.REFUNDED):
            raise RefundError("پرداخت هم‌زمان تغییر کرد؛ صفحه را دوباره باز کنید")  # rolls the order back too
    payment.status = Payment.REFUNDED
    return RefundResult(payment, order_refunded)
```

در `refund_candidates()` فقط این خط عوض می‌شود:

```python
    earlier = Payment.objects.filter(
        order_id=OuterRef("order_id"), status__in=[Payment.VERIFIED, Payment.REFUNDED], pk__lt=OuterRef("pk")
    )
```

**۵.۱.۲ `apps/payments/admin.py`:** اکشن `mark_refunded` به سرویس وصل شود و `from django.utils import timezone` حذف شود:

```python
    @admin.action(description="ثبت بازگشت وجه انجام‌شد", permissions=["manage"])
    def mark_refunded(self, request, queryset):
        ids = list(queryset.filter(pk__in=services.refund_candidates().values("pk")).values_list("pk", flat=True))
        done = failed = 0
        for pk in ids:
            try:
                result = services.record_refund(pk, by=request.user, note="ثبت از ادمین")
            except services.RefundError:
                failed += 1
                continue
            self.log_change(request, result.payment, "بازگشت وجه ثبت شد")
            done += 1
        self.message_user(
            request,
            f"{done} پرداخت به‌عنوان بازگشت‌خورده ثبت شد، {failed} مورد مجاز نبود.",
            messages.SUCCESS if not failed else messages.WARNING,
        )
```

**۵.۱.۳ `apps/orders/admin.py`:** بازگشت وجه از فرم وضعیت کنار گذاشته شود.

```python
def _staff_targets(order) -> list[str]:
    """Refunds are recorded on the payment (payments.services.record_refund), never as a bare status move."""
    return [target for target in workflow.allowed_targets(order) if target != Order.REFUNDED]
```

در `StatusForm.__init__` به‌جای `workflow.allowed_targets(order)` از `_staff_targets(order)` استفاده کن، و در `OrderAdmin.change_view` مقدار `"has_targets": bool(order and _staff_targets(order))`.

**۵.۱.۴ `apps/orders/notify.py`:**

```python
def has_status_sms(order: Order) -> bool:
    """True when the current status has an SMS at all (the «resend» button is hidden otherwise)."""
    return _message(order) is not None
```

**۵.۱.۵ `apps/orders/shipping.py`:**

```python
# [VERIFY] docs/vendors/neshan/: replace with a documented share link if there is one.
MAP_LINK = "https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"


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

### ۵.۲ منطق پنل

**۵.۲.۱ `apps/panel/queries.py`** (جدید):

```python
"""Query helpers shared by panel views, search providers and the dashboard."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db.models import Q, QuerySet, Sum
from django.utils import timezone

from apps.core.cache import safe_cache_get, safe_cache_set
from apps.core.jalali_forms import parse_jalali_safe
from apps.core.text import normalize_fa
from apps.orders.models import PAID_STATES, Order

SALES_TTL = 60  # D44: dashboard numbers may be cached for at most 60 s


def order_search_q(raw: str) -> Q | None:
    """Number, tracking code, names, or (part of) a mobile number; Persian digits are fine."""
    text = normalize_fa(raw)[:40].strip()
    if not text:
        return None
    condition = (
        Q(number__icontains=text)
        | Q(tracking_code__icontains=text)
        | Q(buyer_name__icontains=text)
        | Q(recipient_name__icontains=text)
    )
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        condition |= Q(buyer_mobile__contains=digits) | Q(recipient_mobile__contains=digits)
    return condition


def day_range(raw_from: str | None, raw_to: str | None):
    """Jalali days -> [low, high) aware datetimes in Tehran. The end day is included; a reversed range is swapped."""
    start, end = parse_jalali_safe(raw_from), parse_jalali_safe(raw_to)
    if start and end and start > end:
        start, end = end, start
    low = timezone.make_aware(datetime.combine(start, time.min)) if start else None
    high = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min)) if end else None
    return low, high


def within(queryset: QuerySet, field: str, low, high) -> QuerySet:
    if low is not None:
        queryset = queryset.filter(**{f"{field}__gte": low})
    if high is not None:
        queryset = queryset.filter(**{f"{field}__lt": high})
    return queryset


def orders_to_ship() -> int:
    return Order.objects.filter(status__in=(Order.PAID, Order.PROCESSING)).count()


def sales_last_30_days() -> int:
    cached = safe_cache_get("panel:sales30")
    if isinstance(cached, int):
        return cached
    since = timezone.now() - timedelta(days=30)
    total = Order.objects.filter(status__in=PAID_STATES, paid_at__gte=since).aggregate(t=Sum("payable"))["t"] or 0
    safe_cache_set("panel:sales30", total, SALES_TTL)
    return total


def ship_queue(user) -> dict:
    rows = list(Order.objects.filter(status__in=(Order.PAID, Order.PROCESSING)).order_by("paid_at", "pk")[:5])
    return {"queue": rows, "can_manage": user.has_perm("orders.manage_order_status")}
```

**۵.۲.۲ `apps/panel/providers.py`** (جدید؛ فازهای بعد همین‌جا اضافه می‌کنند):

```python
"""Search providers and navigation badges. Every panel phase appends its own here."""

from __future__ import annotations

from django.urls import reverse

from apps.orders.models import Order
from apps.panel import badges, queries, search
from apps.payments import services as payment_services


@badges.register("orders_to_ship")
def orders_to_ship() -> int:
    return queries.orders_to_ship()


@badges.register("refunds")
def refunds() -> int:
    return payment_services.refund_candidates().count()


@search.register("orders", "سفارش‌ها", "orders.view_order")
def find_orders(query: str) -> list[search.Hit]:
    condition = queries.order_search_q(query)
    if condition is None:
        return []
    rows = Order.objects.filter(condition).order_by("-created_at")[: search.PER_PROVIDER]
    return [
        search.Hit(o.number, f"{o.buyer_name} — {o.get_status_display()}", reverse("panel:order_detail", args=[o.number]))
        for o in rows
    ]
```

**۵.۲.۳ `apps/panel/nav.py`** (دو ردیف به `ITEMS` اضافه شود):

```python
    NavItem("orders", "سفارش‌ها", "panel:orders", icon="shopping-bag", group="daily",
            perms=("orders.view_order",), badge="orders_to_ship"),
    NavItem("payments", "پرداخت‌ها", "panel:payments", icon="credit-card", group="daily",
            perms=("payments.view_payment",), badge="refunds"),
```

اگر آیکونی در `static/src/sprite.svg` نبود، نزدیک‌ترین آیکون موجود را بگذار.

**۵.۲.۴ `apps/panel/views/orders.py`:**

```python
"""Orders in the panel: list, detail and staff status moves (docs/09 module 2).

Every status change goes through workflow.change_status; this module never writes an Order itself.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts import ratelimit
from apps.core.jalali import to_fa_digits
from apps.orders import notify, shipping, workflow
from apps.orders.invoice import render_invoice
from apps.orders.models import PAID_STATES, Order
from apps.panel import audit, htmx, queries
from apps.panel.forms import StatusChangeForm
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services
from apps.payments.models import Payment

PAGE_SIZE = 25
VIEW, MANAGE = "orders.view_order", "orders.manage_order_status"
TABS = (
    ("todo", "نیازمند اقدام", (Order.PAID, Order.PROCESSING)),
    ("shipped", "ارسال‌شده", (Order.SHIPPED,)),
    ("delivered", "تحویل‌شده", (Order.DELIVERED,)),
    ("closed", "لغو و بازگشت وجه", (Order.CANCELLED, Order.EXPIRED, Order.REFUNDED)),
    ("pending", "در انتظار پرداخت", (Order.PENDING,)),
    ("all", "همه", None),
)
TAB_STATUSES = {code: statuses for code, _label, statuses in TABS}
DONE = {
    Order.PROCESSING: "سفارش در حال آماده‌سازی است",
    Order.SHIPPED: "ارسال ثبت شد",
    Order.DELIVERED: "تحویل سفارش ثبت شد",
    Order.CANCELLED: "سفارش لغو شد",
}
RANK = {Order.PENDING: 1, Order.PAID: 2, Order.PROCESSING: 3, Order.SHIPPED: 4, Order.DELIVERED: 5}
STEP_LABELS = ("ثبت", "پرداخت", "آماده‌سازی", "ارسال", "تحویل")


# --- list -----------------------------------------------------------------


def _tab_counts() -> dict[str, int]:
    by_status = dict(Order.objects.order_by().values_list("status").annotate(n=Count("pk")))  # one query
    return {
        code: sum(by_status.values()) if statuses is None else sum(by_status.get(s, 0) for s in statuses)
        for code, _label, statuses in TABS
    }


def _list_context(params, user) -> dict:
    tab = params.get("tab") if params.get("tab") in TAB_STATUSES else "todo"
    queryset = Order.objects.all()
    if TAB_STATUSES[tab] is not None:
        queryset = queryset.filter(status__in=TAB_STATUSES[tab])
    condition = queries.order_search_q(params.get("q", ""))
    if condition is not None:
        queryset = queryset.filter(condition)
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))
    queryset = queryset.order_by("paid_at", "pk") if tab == "todo" else queryset.order_by("-created_at", "-pk")

    page_obj = Paginator(queryset, PAGE_SIZE).get_page(params.get("page"))
    counts = _tab_counts()
    filters = {key: params.get(key, "") for key in ("q", "from", "to") if params.get(key)}
    return {
        "tab": tab,
        "tabs": [(code, label, counts[code]) for code, label, _statuses in TABS],
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "date_from": params.get("from", ""),
        "date_to": params.get("to", ""),
        "filter_qs": urlencode(filters),
        "qs": urlencode({"tab": tab, **filters}),
        "hidden": [("tab", tab), ("page", page_obj.number), *filters.items()],
        "show_select": tab == "todo" and user.has_perm(MANAGE),
    }


@panel_view(VIEW)
@require_GET
def order_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/orders/_list_results.html", context)
    return render(request, "panel/orders/list.html", context)


@panel_view(VIEW, MANAGE)
@require_POST
def order_bulk(request):
    """«شروع آماده‌سازی» for the selected paid orders; also the one-click button of the dashboard queue."""
    numbers = set(request.POST.getlist("order")[:100])
    ids = Order.objects.filter(number__in=numbers, status=Order.PAID).values_list("pk", flat=True)
    done = 0
    for pk in list(ids):
        try:
            workflow.change_status(pk, Order.PROCESSING, by=request.user)
        except workflow.TransitionError:
            continue  # someone else moved it meanwhile
        done += 1
    skipped = len(numbers) - done
    message = to_fa_digits(f"{done} سفارش در حال آماده‌سازی شد" + (f"، {skipped} مورد مجاز نبود" if skipped else ""))
    level = "success" if done and not skipped else "warning"
    if not numbers:
        message, level = "سفارشی انتخاب نشده است", "error"

    if not request.htmx:
        htmx.flash(request, message, level)
        return redirect("panel:orders")
    if request.POST.get("ctx") == "dashboard":
        response = render(request, "panel/partials/_ship_queue.html", queries.ship_queue(request.user))
    else:
        response = render(request, "panel/orders/_list_results.html", _list_context(request.POST, request.user))
    return htmx.toast(response, message, level)


# --- detail ---------------------------------------------------------------


def _load(number: str) -> Order:
    return get_object_or_404(
        Order.objects.select_related("shipping_method").prefetch_related("items", "payments", "status_logs__by_user"),
        number=number,
    )


def _steps(order: Order):
    rank = RANK.get(order.status)  # cancelled / expired / refunded show their own status instead
    return [(label, index <= rank) for index, label in enumerate(STEP_LABELS, 1)] if rank else None


def _detail_context(order: Order, user) -> dict:
    labels = dict(Order.STATUS_CHOICES)
    payments = list(order.payments.all())
    targets = workflow.allowed_targets(order)
    verified = [p for p in payments if p.status == Payment.VERIFIED]
    return {
        "order": order,
        "items": list(order.items.all()),
        "payments": payments,
        "refund_ids": set(payment_services.refund_candidates().filter(order=order).values_list("pk", flat=True)),
        "refund_payment": min(verified, key=lambda p: p.pk) if verified and Order.REFUNDED in targets else None,
        "logs": [
            {
                "log": log,
                "from_label": labels.get(log.from_status, ""),
                "to_label": labels.get(log.to_status, log.to_status),
                "by": (log.by_user.get_full_name() or log.by_user.mobile) if log.by_user else "",
            }
            for log in order.status_logs.all()
        ],
        "steps": _steps(order),
        "can_manage": user.has_perm(MANAGE),
        "can_refund": user.has_perms((MANAGE, "payments.view_payment")),
        "can_start": Order.PROCESSING in targets,
        "can_ship": Order.SHIPPED in targets,
        "can_deliver": Order.DELIVERED in targets,
        "can_cancel": Order.CANCELLED in targets,
        "can_invoice": order.status in PAID_STATES,
        "can_resend": notify.has_status_sms(order),
        "needs_tracking": shipping.has_tracking(order),
        "tracking_page": shipping.tracking_page(order),
        "recipient_text": shipping.recipient_text(order),
        "map_link": shipping.map_link(order),
    }


def _detail_response(request, number: str, message: str = "", level: str = "success"):
    """Errors are answered with 200 too: htmx does not swap 4xx, and the toast carries the message."""
    if not request.htmx:
        if message:
            htmx.flash(request, message, level)
        return redirect("panel:order_detail", number=number)
    response = render(request, "panel/orders/_detail_body.html", _detail_context(_load(number), request.user))
    return htmx.toast(response, message, level) if message else response


@panel_view(VIEW)
@require_GET
def order_detail(request, number):
    return render(request, "panel/orders/detail.html", _detail_context(_load(number), request.user))


@panel_view(VIEW, MANAGE)
@require_POST
def order_status(request, number):
    order = get_object_or_404(Order, number=number)
    form = StatusChangeForm(request.POST)
    if not form.is_valid():
        return _detail_response(request, number, form.first_error(), "error")
    data = form.cleaned_data
    try:
        workflow.change_status(
            order.pk, data["to"], by=request.user, tracking_code=data["tracking_code"], note=data["note"]
        )
    except workflow.TransitionError as exc:  # illegal move, missing tracking code, or a stale page
        return _detail_response(request, number, str(exc), "error")
    return _detail_response(request, number, DONE[data["to"]])


@panel_view(VIEW, MANAGE)
@require_POST
def order_resend_sms(request, number):
    order = get_object_or_404(Order.objects.select_related("shipping_method"), number=number)
    if not notify.has_status_sms(order):
        return _detail_response(request, number, "برای این وضعیت پیامکی تعریف نشده است", "error")
    if not ratelimit.consume(f"panel:sms:{order.pk}", 3, ratelimit.HOUR):
        return _detail_response(request, number, "پیامک این سفارش در ساعت گذشته چند بار ارسال شده؛ بعداً تلاش کنید", "error")
    notify.send_status_sms(order.pk)  # no transaction is open here
    audit.log(request.user, order, audit.CHANGE, "ارسال دوباره‌ی پیامک وضعیت")
    return _detail_response(request, number, "پیامک ارسال شد؛ نتیجه در لاگ پیامک ثبت می‌شود")


@panel_view(VIEW)
@require_GET
def order_invoice(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number, status__in=PAID_STATES)
    return render_invoice(request, order)
```

**۵.۲.۵ `apps/panel/views/payments.py`** (فایل کامل؛ ادامه‌ی ناقص قبلی دور انداخته شود):

```python
"""Payments in the panel: the refund report, and the one place a refund is recorded (docs/09 module 3)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.core.text import normalize_fa
from apps.panel import audit, auth, htmx, queries
from apps.panel.permissions import panel_view
from apps.payments import services as payment_services
from apps.payments.models import Payment

PAGE_SIZE = 25
VIEW, MANAGE = "payments.view_payment", "orders.manage_order_status"


def _list_context(params, user) -> dict:
    tab = "all" if params.get("tab") == "all" else "refund"
    base = payment_services.refund_candidates() if tab == "refund" else Payment.objects.all()
    queryset = base.select_related("order")
    if params.get("status") in dict(Payment.STATUS_CHOICES):
        queryset = queryset.filter(status=params["status"])
    if params.get("gateway"):
        queryset = queryset.filter(gateway_code=params["gateway"])
    text = normalize_fa(params.get("q", ""))[:40]
    if text:
        queryset = queryset.filter(
            Q(order__number__icontains=text) | Q(authority__icontains=text) | Q(ref_id__icontains=text)
        )
    queryset = queries.within(queryset, "created_at", *queries.day_range(params.get("from"), params.get("to")))

    page_obj = Paginator(queryset.order_by("-created_at", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {key: params.get(key, "") for key in ("q", "status", "gateway", "from", "to") if params.get(key)}
    can_refund = user.has_perm(MANAGE)
    candidate_ids = (
        set(
            payment_services.refund_candidates()
            .filter(pk__in=[p.pk for p in page_obj.object_list])
            .values_list("pk", flat=True)
        )
        if can_refund
        else set()
    )
    return {
        "tab": tab,
        "tabs": [
            ("refund", "نیازمند بازگشت وجه", payment_services.refund_candidates().count()),
            ("all", "همه", Payment.objects.count()),
        ],
        "page_obj": page_obj,
        "q": params.get("q", ""),
        "date_from": params.get("from", ""),
        "date_to": params.get("to", ""),
        "status": params.get("status", ""),
        "gateway": params.get("gateway", ""),
        "status_choices": Payment.STATUS_CHOICES,
        "gateways": sorted(set(Payment.objects.order_by().values_list("gateway_code", flat=True))),
        "filter_qs": urlencode(filters),
        "qs": urlencode({"tab": tab, **filters}),
        "hidden": [("tab", tab), ("page", page_obj.number), *filters.items()],
        "can_refund": can_refund,
        "candidate_ids": candidate_ids,
    }


@panel_view(VIEW)
@require_GET
def payment_list(request):
    context = _list_context(request.GET, request.user)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/payments/_list_results.html", context)
    return render(request, "panel/payments/list.html", context)


@panel_view(VIEW, MANAGE)
@require_POST
def payment_refund(request, pk):
    """The only write of the payments section; the rules live in payments.services.record_refund."""
    get_object_or_404(Payment, pk=pk)
    note = " ".join(request.POST.get("note", "").split())[:200]
    if request.POST.get("confirm") != "1":
        message, level = "تایید کنید که مبلغ را از درگاه برگردانده‌اید", "error"
    else:
        try:
            result = payment_services.record_refund(pk, by=request.user, note=note)
        except payment_services.RefundError as exc:
            message, level = str(exc), "error"
        else:
            audit.log(request.user, result.payment, audit.CHANGE, f"بازگشت وجه ثبت شد: {note}")
            message, level = "بازگشت وجه ثبت شد", "success"

    if request.htmx:  # only the payments list posts with HTMX; the order page posts normally
        response = render(
            request, "panel/payments/_list_results.html", _list_context(request.POST, request.user)
        )
        return htmx.toast(response, message, level)
    htmx.flash(request, message, level)
    return redirect(auth.safe_next(request, request.POST.get("next")))
```

**۵.۲.۶ `apps/panel/urls.py`** (جایگزین کامل):

```python
from __future__ import annotations

from django.urls import path

from .views import account, auth, dashboard, orders, payments, shell

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
    path("orders/bulk/", orders.order_bulk, name="order_bulk"),  # before <number>
    path("orders/<str:number>/", orders.order_detail, name="order_detail"),
    path("orders/<str:number>/status/", orders.order_status, name="order_status"),
    path("orders/<str:number>/sms/", orders.order_resend_sms, name="order_resend_sms"),
    path("orders/<str:number>/invoice/", orders.order_invoice, name="order_invoice"),
    path("payments/", payments.payment_list, name="payments"),
    path("payments/<int:pk>/refund/", payments.payment_refund, name="payment_refund"),
]
```

**۵.۲.۷ `apps/panel/views/dashboard.py`** (جایگزین کامل): کارت‌های «نظر» و «موجودی» در P12 می‌آیند. فعلاً هیچ لینک `[TEMP]` و هیچ عدد ساختگی نیست.

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
    context = {
        "can_orders": can_orders,
        "refunds": payment_services.refund_candidates().count() if user.has_perm("payments.view_payment") else 0,
    }
    if can_orders:
        context.update(
            to_ship=queries.orders_to_ship(), sales=queries.sales_last_30_days(), **queries.ship_queue(user)
        )
    return render(request, "panel/dashboard.html", context)
```

### ۵.۳ قالب‌ها

همه زیر `templates/panel/` و همه با `{% load %}` خودشان. فایل‌های `login_form.html` و `partials/_mm_dialog` قدیمی حذف می‌شوند. آیکون‌های تازه: `menu search shopping-bag credit-card copy printer arrow-left user log-out alert-circle truck x info package`. اگر `build_sprite.py` آیکونی را پیدا نکرد، نزدیک‌ترین آیکون موجود جایگزین شود.

#### `panel/base.html` (سند HTML بدون قاب؛ ورود هم از همین ارث می‌برد)

```html
{% load static %}<!DOCTYPE html>
<html lang="fa" dir="rtl" data-theme="malmal">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="robots" content="noindex,nofollow">
  <title>{% block title %}پنل{% endblock %} — {{ site_settings.store_name }}</title>
  <link rel="icon" href="{% static 'favicon/favicon.ico' %}" sizes="any">
  <script>
    (function () {
      var pref = "system";
      try { pref = localStorage.getItem("malmal.theme") || "system"; } catch (e) {}
      var dark = pref === "dark" || (pref !== "light" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
      document.documentElement.setAttribute("data-theme", dark ? "malmal-dark" : "malmal");
      document.documentElement.dataset.themePref = pref;
    })();
  </script>
  <link rel="stylesheet" href="{% static 'css/app.css' %}">
</head>
<body class="bg-base-200 text-base-content min-h-screen" hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  <div id="toasts" class="toast toast-top toast-center z-50" aria-live="polite"></div>
  {% block body %}{% endblock %}
  {% include "partials/_mm_dialog.html" %}
  <script src="{% static 'js/htmx.min.js' %}" defer></script>
  <script src="{% static 'js/mm/core.js' %}" defer></script>
  <script src="{% static 'js/mm/ui.js' %}" defer></script>
  <script src="{% static 'js/mm/forms.js' %}" defer></script>
  <script src="{% static 'js/mm/theme.js' %}" defer></script>
  <script src="{% static 'js/mm/shell.js' %}" defer></script>
  <script src="{% static 'js/mm/panel.js' %}" defer></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

#### `panel/shell.html` (قاب با کشو و نوار بالا)

```html
{% extends "panel/base.html" %}
{% load core_tags panel_tags %}
{% block body %}
<div class="drawer lg:drawer-open">
  <input id="panel-drawer" type="checkbox" class="drawer-toggle">
  <div class="drawer-content flex flex-col min-w-0">
    <header class="bg-base-100 border-b sticky top-0 z-30">
      <div class="h-14 px-4 lg:px-6 flex items-center gap-3">
        <label for="panel-drawer" class="btn btn-ghost btn-square w-10 h-10 lg:hidden" aria-label="منو">{% icon "menu" size=20 %}</label>

        <div class="relative flex-1 max-w-xl" role="search" data-panel-search>
          <label class="input h-10 w-full bg-base-200 flex items-center gap-2">
            {% icon "search" size=18 class="text-ink-3" %}
            <input type="search" name="q" placeholder="جستجو: سفارش، موبایل، کد رهگیری" class="grow text-small" autocomplete="off"
                   aria-label="جستجوی سراسری"
                   hx-get="{% url 'panel:search' %}" hx-trigger="input changed delay:300ms, search"
                   hx-target="#search-results" hx-swap="innerHTML" hx-indicator="#search-indicator">
            <span id="search-indicator" class="htmx-indicator loading loading-spinner loading-xs" aria-hidden="true"></span>
          </label>
          <div id="search-results" class="hidden absolute top-full start-0 end-0 mt-1 z-50 bg-base-100 border rounded-box surface-float max-h-96 overflow-y-auto" aria-live="polite"></div>
        </div>

        <a href="{% url 'core:home' %}" target="_blank" rel="noopener" class="btn btn-ghost h-10 px-3 text-small font-normal hidden sm:inline-flex">مشاهده‌ی فروشگاه</a>

        <details class="dropdown dropdown-end">
          <summary class="btn btn-ghost h-10 px-3 gap-2 text-small font-normal list-none">
            {% icon "user" size=18 class="text-ink-2" %}
            <span class="hidden sm:inline">{{ request.user.get_full_name|default:request.user.mobile|fa_text }}</span>
          </summary>
          <ul class="dropdown-content menu bg-base-100 rounded-box border surface-float w-56 p-2 mt-2 z-40">
            <li><a href="{% url 'panel:account' %}" class="text-small">حساب من</a></li>
            <li>
              <div class="flex items-center justify-between gap-2">
                <span class="text-label text-ink-3">پوسته</span>
                <span class="flex items-center gap-1">
                  <button type="button" data-theme-choice="light" class="btn btn-ghost btn-xs px-2">روشن</button>
                  <button type="button" data-theme-choice="dark" class="btn btn-ghost btn-xs px-2">تاریک</button>
                  <button type="button" data-theme-choice="system" class="btn btn-ghost btn-xs px-2">سیستم</button>
                </span>
              </div>
            </li>
            <li>
              <form method="post" action="{% url 'panel:logout' %}">{% csrf_token %}
                <button type="submit" class="text-small w-full text-start">خروج</button>
              </form>
            </li>
          </ul>
        </details>
      </div>
    </header>

    <main id="main-content" class="flex-1 w-full max-w-7xl mx-auto px-4 lg:px-6 py-6 pb-28 lg:pb-6">
      {% for message in messages %}
        <div role="alert" class="alert {% if message.tags == 'error' %}alert-error{% elif message.tags == 'success' %}alert-success{% elif message.tags == 'warning' %}alert-warning{% else %}alert-info{% endif %} text-small mb-4"><span>{{ message }}</span></div>
      {% endfor %}
      {% block content %}{% endblock %}
    </main>
  </div>

  <div class="drawer-side z-40">
    <label for="panel-drawer" aria-label="بستن منو" class="drawer-overlay"></label>
    <aside class="bg-base-100 border-e w-64 min-h-full p-4 flex flex-col gap-4">
      <a href="{% url 'panel:dashboard' %}" class="flex items-center gap-2 py-1">
        {% include "partials/_logo.html" with img_class="h-9 w-auto" brand_class="text-lead leading-none" %}
      </a>
      <nav aria-label="ناوبری پنل" class="flex-1">{% render_sidebar %}</nav>
      {% if request.user.is_superuser %}
        <a href="{% url 'admin:index' %}" target="_blank" rel="noopener" class="link text-label text-ink-3">ادمین جنگو</a>
      {% endif %}
    </aside>
  </div>
</div>
{% endblock %}
```

#### `panel/partials/sidebar.html`

بج‌ها با `invisible` جا را نگه می‌دارند. `ul` خودش هر ۶۰ ثانیه جایگزین می‌شود.

```html
{% load core_tags panel_tags %}
<ul id="panel-nav" class="menu w-full p-0 gap-1"
    hx-get="{% url 'panel:badges' %}" hx-trigger="every 60s" hx-swap="outerHTML"{% if oob %} hx-swap-oob="outerHTML"{% endif %}>
  {% for group_label, links in groups %}
    <li class="menu-title text-label text-ink-3{% if not forloop.first %} mt-4{% endif %}">{{ group_label }}</li>
    {% for link in links %}
      <li>
        <a href="{{ link.url }}" class="text-small gap-3{% if link.active %} menu-active{% endif %}"{% if link.active %} aria-current="page"{% endif %}>
          {% icon link.item.icon size=18 class="text-ink-2" %}
          <span class="flex-1">{{ link.item.label }}</span>
          {% if link.item.badge %}{% render_badge link.item.badge counts %}{% endif %}
        </a>
      </li>
    {% endfor %}
  {% endfor %}
</ul>
```

#### قالب‌های کوچک مشترک

`panel/partials/badge.html`:

```html
{% load core_tags %}<span class="badge badge-sm bg-base-300 border-0 text-label num min-w-6{% if not visible %} invisible{% endif %}" data-badge="{{ key }}">{{ count|fa_digits }}</span>
```

`panel/partials/_page_heading.html` (امضای دو خط هم‌قد؛ هر صفحه ردیف عمل‌هایش را خودش کنار آن می‌گذارد):

```html
<div class="flex items-center gap-3 min-w-0">
  <span class="inline-flex items-center gap-1 shrink-0" aria-hidden="true">
    <span class="w-0.5 h-4 bg-base-content inline-block"></span>
    <span class="w-0.5 h-4 bg-base-content inline-block"></span>
  </span>
  <h1 class="text-title font-medium truncate">{{ title }}</h1>
</div>
```

`panel/partials/_pagination.html` (لینک نسبی `?...` مثل فروشگاه؛ بعد از POST هم به آدرس صفحه‌ی مرورگر می‌رود، نه آدرس POST):

```html
{% load core_tags %}
{% if page_obj.paginator.num_pages > 1 %}
<nav class="join flex justify-center mt-4" aria-label="صفحه‌بندی">
  {% if page_obj.has_previous %}
    <a class="join-item btn btn-sm" rel="prev" href="?{{ qs }}&page={{ page_obj.previous_page_number }}"
       hx-get="?{{ qs }}&page={{ page_obj.previous_page_number }}" hx-target="{{ target }}" hx-push-url="true">
      {% icon "chevron-right" size=18 flip=True %}<span class="sr-only">صفحه قبل</span></a>
  {% endif %}
  {% for number in page_obj.paginator.page_range %}
    {% if number == page_obj.number %}
      <span class="join-item btn btn-sm bg-base-300 border" aria-current="page">{{ number|fa_digits }}</span>
    {% elif number >= page_obj.number|add:"-2" and number <= page_obj.number|add:"2" %}
      <a class="join-item btn btn-sm" href="?{{ qs }}&page={{ number }}"
         hx-get="?{{ qs }}&page={{ number }}" hx-target="{{ target }}" hx-push-url="true">{{ number|fa_digits }}</a>
    {% endif %}
  {% endfor %}
  {% if page_obj.has_next %}
    <a class="join-item btn btn-sm" rel="next" href="?{{ qs }}&page={{ page_obj.next_page_number }}"
       hx-get="?{{ qs }}&page={{ page_obj.next_page_number }}" hx-target="{{ target }}" hx-push-url="true">
      {% icon "chevron-left" size=18 flip=True %}<span class="sr-only">صفحه بعد</span></a>
  {% endif %}
</nav>
{% endif %}
```

`panel/partials/search_results.html`:

```html
{% load core_tags %}
{% for provider, hits in results %}
  <div class="px-3 pt-3 text-label text-ink-3">{{ provider.label }}</div>
  <ul class="p-1">
    {% for hit in hits %}
      <li><a href="{{ hit.url }}" class="flex flex-col p-2 rounded-field hover:bg-base-300 transition-colors">
        <span class="text-small">{{ hit.title|fa_text }}</span>
        <span class="text-label text-ink-3">{{ hit.subtitle|fa_text }}</span>
      </a></li>
    {% endfor %}
  </ul>
{% empty %}
  <p class="p-3 text-small text-ink-2">نتیجه‌ای پیدا نشد</p>
{% endfor %}
```

`panel/403.html`:

```html
{% extends "panel/shell.html" %}
{% block title %}دسترسی ندارید{% endblock %}
{% block content %}
  {% url 'panel:dashboard' as home %}
  {% include "partials/_empty_state.html" with title="به این بخش دسترسی ندارید" description="اگر لازم است، از مدیر کل بخواهید دسترسی را به حساب شما اضافه کند" action_url=home action_label="بازگشت به داشبورد" %}
{% endblock %}
```

#### ورود و حساب

`panel/login.html`:

```html
{% extends "panel/base.html" %}
{% load core_tags %}
{% block title %}ورود{% endblock %}
{% block body %}
<main class="min-h-screen flex items-center justify-center px-4 py-8">
  <form method="post" action="{% url 'panel:login' %}" class="bg-base-100 border rounded-box p-5 w-full max-w-sm flex flex-col gap-4" novalidate>
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ next }}">
    <h1 class="text-title font-medium">ورود به پنل</h1>
    {% if error %}<div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ error }}</span></div>{% endif %}
    <fieldset class="fieldset">
      <legend class="fieldset-legend text-small font-medium">موبایل</legend>
      <input type="text" name="mobile" value="{{ mobile }}" dir="ltr" inputmode="numeric" autocomplete="username" data-fa-digits data-autofocus class="input w-full text-end num">
    </fieldset>
    <fieldset class="fieldset">
      <legend class="fieldset-legend text-small font-medium">رمز عبور</legend>
      <input type="password" name="password" autocomplete="current-password" class="input w-full" dir="ltr">
    </fieldset>
    <button type="submit" class="btn btn-primary h-11 min-h-11">ورود</button>
  </form>
</main>
{% endblock %}
```

`panel/account.html`:

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}حساب من{% endblock %}
{% block content %}
<div class="max-w-md flex flex-col gap-4">
  {% include "panel/partials/_page_heading.html" with title="حساب من" %}
  <form method="post" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for field in form %}
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">{{ field.label }}</legend>
        {{ field }}
        {% for error in field.errors %}<p class="text-label text-error flex items-center gap-1 mt-1">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ error }}</span></p>{% endfor %}
      </fieldset>
    {% endfor %}
    <button type="submit" class="btn btn-primary h-11 min-h-11">تغییر رمز</button>
  </form>
  <form method="post" action="{% url 'panel:logout_all' %}" data-confirm="از همه‌ی دستگاه‌ها، از جمله همین مرورگر، خارج می‌شوید؟"
        class="bg-base-100 border rounded-box p-4 flex items-center justify-between gap-3">
    {% csrf_token %}
    <span class="text-small text-ink-2">خروج هم‌زمان از همه‌ی دستگاه‌ها</span>
    <button type="submit" class="btn btn-ghost h-10 text-ink-2 text-small">خروج از همه</button>
  </form>
</div>
{% endblock %}
```

#### داشبورد

`panel/dashboard.html`:

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

  {% if can_orders %}
    <section class="grid grid-cols-1 sm:grid-cols-2 gap-3" aria-label="خلاصه">
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
    </section>
    {% include "panel/partials/_ship_queue.html" %}
  {% elif not refunds %}
    {% include "partials/_empty_state.html" with title="هنوز بخشی به حساب شما اضافه نشده" description="از مدیر کل بخواهید دسترسی‌های لازم را بدهد" %}
  {% endif %}
</div>
{% endblock %}
```

`panel/partials/_ship_queue.html` (این partial بعد از «شروع آماده‌سازی» از داشبورد هم تازه می‌شود):

```html
{% load core_tags %}
<section id="ship-queue" class="bg-base-100 border rounded-box p-4 flex flex-col gap-3 min-h-40">
  <div class="flex items-center justify-between gap-3">
    <h2 class="text-lead font-medium">صف ارسال</h2>
    <a href="{% url 'panel:orders' %}" class="text-small text-brand-ink">همه‌ی سفارش‌ها</a>
  </div>
  {% for order in queue %}
    <div class="flex items-center justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
      <a href="{% url 'panel:order_detail' order.number %}" class="min-w-0 flex flex-col">
        <span class="latin text-small font-medium">{{ order.number }}</span>
        <span class="text-label text-ink-3 truncate"><bdi>{{ order.recipient_name|fa_text }}</bdi> — {{ order.city_name|fa_text }}</span>
      </a>
      {% if can_manage and order.status == "paid" %}
        <form method="post" action="{% url 'panel:order_bulk' %}" hx-post="{% url 'panel:order_bulk' %}"
              hx-target="#ship-queue" hx-swap="outerHTML" hx-disabled-elt="find button">
          {% csrf_token %}
          <input type="hidden" name="order" value="{{ order.number }}"><input type="hidden" name="ctx" value="dashboard">
          <button type="submit" class="btn btn-sm h-10 bg-base-300 border shrink-0">شروع آماده‌سازی</button>
        </form>
      {% else %}
        <a href="{% url 'panel:order_detail' order.number %}" class="flex items-center gap-2 text-small shrink-0">
          <span class="status {{ order.status_dot }}"></span>{{ order.get_status_display }}</a>
      {% endif %}
    </div>
  {% empty %}
    <p class="text-small text-ink-2 py-6 text-center">سفارشی منتظر ارسال نیست</p>
  {% endfor %}
</section>
```

#### فهرست سفارش‌ها

`panel/orders/list.html`:

```html
{% extends "panel/shell.html" %}
{% load static %}
{% block title %}سفارش‌ها{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="سفارش‌ها" %}
    <span id="orders-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>

  <form id="orders-filter" action="{% url 'panel:orders' %}" method="get" role="search"
        hx-get="{% url 'panel:orders' %}" hx-target="#orders-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-sync="this:replace"
        hx-include="#orders-tab" hx-indicator="#orders-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3" data-date-range>
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ q }}" placeholder="شماره سفارش، موبایل یا کد رهگیری" class="grow text-small" autocomplete="off">
    </label>
    <input type="text" name="from" value="{{ date_from }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="از تاریخ" class="input h-10 w-36 num text-small">
    <input type="text" name="to" value="{{ date_to }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="تا تاریخ" class="input h-10 w-36 num text-small">
    <span class="hidden text-label text-error" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد</span>
  </form>

  <div id="orders-results" aria-live="polite">{% include "panel/orders/_list_results.html" %}</div>
</div>
{% endblock %}
{% block extra_js %}<script src="{% static 'js/jalali_picker.js' %}" defer></script>{% endblock %}
```

`panel/orders/_list_results.html`:

```html
{% load core_tags jalali_tags %}
<input type="hidden" id="orders-tab" name="tab" value="{{ tab }}">
<div class="flex flex-col gap-4">
  <div role="tablist" class="tabs tabs-border overflow-x-auto no-scrollbar">
    {% for code, label, count in tabs %}
      <a role="tab" class="tab gap-2 whitespace-nowrap{% if code == tab %} tab-active{% endif %}"
         href="?tab={{ code }}{% if filter_qs %}&{{ filter_qs }}{% endif %}"
         hx-get="?tab={{ code }}{% if filter_qs %}&{{ filter_qs }}{% endif %}" hx-target="#orders-results" hx-push-url="true"
         hx-indicator="#orders-indicator">
        {{ label }}<span class="text-label text-ink-3 num">{{ count|fa_digits }}</span>
      </a>
    {% endfor %}
  </div>

  {% if page_obj.object_list %}
    <form id="orders-bulk" method="post" action="{% url 'panel:order_bulk' %}" hx-post="{% url 'panel:order_bulk' %}"
          hx-target="#orders-results" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']">
      {% csrf_token %}
      {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}

      {% if show_select %}
        <div class="hidden lg:flex items-center justify-between gap-3 mb-3">
          <span class="text-small text-ink-2">سفارش‌های «پرداخت‌شده» را انتخاب کنید و آماده‌سازی را شروع کنید</span>
          <button type="submit" class="btn btn-primary h-10 min-h-10">شروع آماده‌سازی انتخاب‌شده‌ها</button>
        </div>
      {% endif %}

      <div class="hidden lg:block bg-base-100 border rounded-box overflow-x-auto">
        <table class="table table-sm">
          <thead><tr>
            {% if show_select %}<th scope="col" class="w-10"><input type="checkbox" data-check-all class="checkbox checkbox-sm" aria-label="انتخاب همه"></th>{% endif %}
            <th scope="col">سفارش</th><th scope="col">خریدار</th><th scope="col">وضعیت</th>
            <th scope="col">مبلغ (تومان)</th><th scope="col">ثبت</th><th scope="col">کد رهگیری</th>
          </tr></thead>
          <tbody>
            {% for o in page_obj.object_list %}
              <tr class="hover:bg-base-300">
                {% if show_select %}<td><input type="checkbox" name="order" value="{{ o.number }}" class="checkbox checkbox-sm" aria-label="انتخاب {{ o.number }}"{% if o.status != "paid" %} disabled{% endif %}></td>{% endif %}
                <td><a href="{% url 'panel:order_detail' o.number %}" class="latin link link-hover font-medium">{{ o.number }}</a></td>
                <td><bdi>{{ o.buyer_name|fa_text }}</bdi><div class="num text-label text-ink-3">{{ o.buyer_mobile|fa_digits }}</div></td>
                <td><span class="flex items-center gap-2 text-small whitespace-nowrap"><span class="status {{ o.status_dot }}"></span>{{ o.get_status_display }}</span></td>
                <td class="whitespace-nowrap">{{ o.payable|toman }}</td>
                <td class="text-ink-2 whitespace-nowrap"><span class="num">{{ o.created_at|to_jalali }}</span></td>
                <td>{% if o.tracking_code %}<span class="latin">{{ o.tracking_code }}</span>{% endif %}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <ul class="lg:hidden flex flex-col gap-3">
        {% for o in page_obj.object_list %}
          <li><a href="{% url 'panel:order_detail' o.number %}" class="block bg-base-100 border rounded-box p-4 flex flex-col gap-2">
            <span class="flex items-center justify-between gap-2">
              <span class="latin text-small font-medium">{{ o.number }}</span>
              <span class="flex items-center gap-2 text-small"><span class="status {{ o.status_dot }}"></span>{{ o.get_status_display }}</span>
            </span>
            <span class="flex items-center justify-between gap-2 text-label text-ink-3">
              <span><bdi>{{ o.buyer_name|fa_text }}</bdi> — <span class="num">{{ o.created_at|to_jalali }}</span></span>
              <span class="text-small text-base-content whitespace-nowrap">{{ o.payable|toman }} تومان</span>
            </span>
          </a></li>
        {% endfor %}
      </ul>
    </form>
    {% include "panel/partials/_pagination.html" with target="#orders-results" %}
  {% else %}
    {% include "partials/_empty_state.html" with title="سفارشی پیدا نشد" description="فیلترها را تغییر دهید یا تب دیگری را ببینید" %}
  {% endif %}
</div>
```

#### جزئیات سفارش

`panel/orders/detail.html`:

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}سفارش {{ order.number }}{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center gap-3 min-w-0">
    <a href="{% url 'panel:orders' %}" class="btn btn-ghost btn-square w-10 h-10 shrink-0" aria-label="بازگشت به فهرست">{% icon "arrow-left" size=18 flip=True %}</a>
    <span class="inline-flex items-center gap-1 shrink-0" aria-hidden="true"><span class="w-0.5 h-4 bg-base-content inline-block"></span><span class="w-0.5 h-4 bg-base-content inline-block"></span></span>
    <h1 class="text-title font-medium truncate">سفارش <span class="latin">{{ order.number }}</span></h1>
  </div>
  <div id="order-body">{% include "panel/orders/_detail_body.html" %}</div>
</div>
{% endblock %}
```

`panel/orders/_primary_action.html` (دو بار include می‌شود: ستون اقدام دسکتاپ و نوار چسبان موبایل):

```html
{% if can_manage %}
  {% if can_start %}
    <form method="post" action="{% url 'panel:order_status' order.number %}" hx-post="{% url 'panel:order_status' order.number %}"
          hx-target="#order-body" hx-swap="innerHTML" hx-disabled-elt="find button">
      {% csrf_token %}<input type="hidden" name="to" value="processing">
      <button type="submit" class="btn btn-primary {{ btn_class }}">شروع آماده‌سازی</button>
    </form>
  {% elif can_ship %}
    <button type="button" popovertarget="ship-modal" class="btn btn-primary {{ btn_class }}">ثبت ارسال</button>
  {% elif can_deliver %}
    <form method="post" action="{% url 'panel:order_status' order.number %}" hx-post="{% url 'panel:order_status' order.number %}"
          hx-target="#order-body" hx-swap="innerHTML" hx-disabled-elt="find button">
      {% csrf_token %}<input type="hidden" name="to" value="delivered">
      <button type="submit" class="btn btn-primary {{ btn_class }}">ثبت تحویل</button>
    </form>
  {% endif %}
{% endif %}
```

`panel/orders/_detail_body.html`:

```html
{% load core_tags jalali_tags panel_tags %}
{% if steps %}
  <ul class="steps w-full text-small">{% for label, done in steps %}<li class="step{% if done %} step-neutral{% endif %}">{{ label }}</li>{% endfor %}</ul>
{% else %}
  <div class="flex items-center gap-2 text-small"><span class="status {{ order.status_dot }}"></span>{{ order.get_status_display }}
    {% if order.cancel_reason %}<span class="text-ink-3">— {{ order.cancel_reason|fa_text }}</span>{% endif %}</div>
{% endif %}

{% if refund_ids %}
  <div role="alert" class="alert text-small">{% icon "alert-circle" size=18 class="text-ink-2 shrink-0" %}
    <span>این سفارش پرداخت تاییدشده‌ای دارد که باید برگردانده شود. مبلغ را از پنل زرین‌پال برگردانید و بعد ثبت کنید</span></div>
{% endif %}

<div class="lg:grid lg:grid-cols-[1fr_320px] lg:gap-6 items-start flex flex-col gap-4">
  <div class="flex flex-col gap-4 min-w-0 w-full">
    <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
      <h2 class="text-lead font-medium">اقلام</h2>
      <ul class="flex flex-col divide-y">
        {% for item in items %}
          <li class="flex items-center gap-3 py-3 first:pt-0">
            <span class="w-14 h-14 shrink-0 rounded-lg bg-white border overflow-hidden flex items-center justify-center">
              {% if item.image_url %}<img src="{{ item.image_url }}" alt="" width="56" height="56" loading="lazy" class="w-full h-full object-contain p-1">{% else %}{% icon "package" size=18 class="text-ink-3" %}{% endif %}
            </span>
            <span class="min-w-0 flex-1 flex flex-col">
              <span class="text-small leading-6 line-clamp-2">{{ item.product_title|fa_text }}</span>
              <span class="text-label text-ink-3">{{ item.variant_title|fa_text }} — <span class="latin">{{ item.sku }}</span> — {{ item.qty|fa_digits }} عدد</span>
            </span>
            <span class="text-small whitespace-nowrap shrink-0">{{ item.line_total|toman }}</span>
          </li>
        {% endfor %}
      </ul>
      <div class="flex flex-col gap-2 border-t pt-3 text-small">
        <div class="flex justify-between"><span class="text-ink-2">جمع کالاها</span><span class="whitespace-nowrap">{{ order.items_total|toman }} تومان</span></div>
        <div class="flex justify-between"><span class="text-ink-2">ارسال</span><span class="text-ink-2">{% if order.shipping_payment_mode == "collect" %}پس‌کرایه{% else %}{{ order.shipping_cost|toman }} تومان{% endif %}</span></div>
        <div class="flex justify-between text-lead font-medium"><span>مبلغ سفارش</span><span class="whitespace-nowrap">{{ order.payable|toman }} تومان</span></div>
      </div>
    </section>

    <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <h2 class="text-lead font-medium">گیرنده و آدرس</h2>
        <button type="button" data-copy="recipient-text" class="btn btn-ghost btn-sm h-10 gap-1">{% icon "copy" size=16 %}<span>کپی مشخصات</span></button>
      </div>
      <p class="text-small"><bdi>{{ order.recipient_name|fa_text }}</bdi> — <span class="num">{{ order.recipient_mobile|fa_digits }}</span></p>
      <p class="text-small text-ink-2 leading-6">{{ order.province_name }}، {{ order.city_name }}، {{ order.address_text|fa_text }}</p>
      <p class="text-label text-ink-3">پلاک {{ order.plate|fa_digits }}{% if order.unit %}، واحد {{ order.unit|fa_digits }}{% endif %} — کدپستی <span class="num">{{ order.postal_code|fa_digits }}</span></p>
      {% if map_link %}<a href="{{ map_link }}" target="_blank" rel="noopener" class="link text-small self-start">نمایش روی نقشه</a>{% endif %}
      <textarea id="recipient-text" class="hidden" readonly>{{ recipient_text }}</textarea>
    </section>

    <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-2">
      <h2 class="text-lead font-medium">خریدار</h2>
      <p class="text-small"><bdi>{{ order.buyer_name|fa_text }}</bdi> — <span class="num">{{ order.buyer_mobile|fa_digits }}</span></p>
      <p class="text-label text-ink-3">کد ملی <span class="num">{{ order.buyer_national_code|fa_digits }}</span>{% if order.buyer_email %} — <span class="latin">{{ order.buyer_email }}</span>{% endif %}</p>
    </section>

    <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
      <h2 class="text-lead font-medium">پرداخت‌ها</h2>
      {% for p in payments %}
        <div class="flex items-center justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
          <span class="min-w-0 flex flex-col">
            <span class="flex items-center gap-2 text-small"><span class="status {{ p.status|payment_dot }}"></span>{{ p.get_status_display }} — <span class="whitespace-nowrap">{{ p.amount|toman }} تومان</span></span>
            <span class="text-label text-ink-3"><span class="latin">{{ p.gateway_code }}</span>{% if p.ref_id %} — تراکنش <span class="latin">{{ p.ref_id }}</span>{% endif %} — <span class="num">{{ p.created_at|to_jalali }}</span></span>
          </span>
          {% if can_refund and p.pk in refund_ids %}
            <button type="button" popovertarget="refund-{{ p.pk }}" class="btn btn-sm h-10 bg-base-300 border shrink-0">ثبت بازگشت وجه</button>
          {% endif %}
        </div>
      {% empty %}
        <p class="text-small text-ink-2">پرداختی ثبت نشده است</p>
      {% endfor %}
    </section>

    <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
      <h2 class="text-lead font-medium">تاریخچه</h2>
      <ul class="flex flex-col gap-3">
        {% for row in logs %}
          <li class="flex flex-col gap-1 text-small">
            <span>{% if row.from_label %}{{ row.from_label }} ← {% endif %}{{ row.to_label }}</span>
            <span class="text-label text-ink-3"><span class="num">{{ row.log.created_at|to_jalali }}</span>{% if row.by %} — <bdi>{{ row.by|fa_text }}</bdi>{% endif %}{% if row.log.note %} — {{ row.log.note|fa_text }}{% endif %}</span>
          </li>
        {% endfor %}
      </ul>
    </section>
  </div>

  <aside class="bg-base-100 border rounded-box p-4 flex flex-col gap-3 w-full lg:sticky lg:top-20">
    <h2 class="text-lead font-medium">اقدام</h2>
    {% if order.tracking_code %}
      <p class="text-small text-ink-2">کد رهگیری: <span class="latin">{{ order.tracking_code }}</span>{% if tracking_page %} — <a href="{{ tracking_page }}" target="_blank" rel="noopener" class="link">رهگیری در سایت تیپاکس</a>{% endif %}</p>
    {% endif %}
    {% include "panel/orders/_primary_action.html" with btn_class="w-full h-11 min-h-11 hidden lg:inline-flex" %}
    <div class="flex flex-wrap gap-2">
      {% if can_invoice %}<a href="{% url 'panel:order_invoice' order.number %}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm h-10 gap-1">{% icon "printer" size=16 %}<span>چاپ فاکتور</span></a>{% endif %}
      {% if can_manage and can_resend %}
        <button type="button" class="btn btn-ghost btn-sm h-10" hx-post="{% url 'panel:order_resend_sms' order.number %}" hx-target="#order-body" hx-swap="innerHTML" hx-disabled-elt="this">ارسال دوباره‌ی پیامک</button>
      {% endif %}
      {% if can_manage and can_cancel %}<button type="button" popovertarget="cancel-modal" class="btn btn-ghost btn-sm h-10 text-ink-2">لغو سفارش</button>{% endif %}
      {% if can_refund and refund_payment %}<button type="button" popovertarget="refund-{{ refund_payment.pk }}" class="btn btn-ghost btn-sm h-10 text-ink-2">ثبت بازگشت وجه</button>{% endif %}
    </div>
  </aside>
</div>

{# D28: the main action sits at the start (right), the amount at the end #}
{% if can_manage %}{% if can_start or can_ship or can_deliver %}
  <div class="lg:hidden fixed bottom-0 inset-x-0 z-20 bg-base-100 border-t px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
    <div class="flex items-center gap-3">
      <div class="flex-1 min-w-0">{% include "panel/orders/_primary_action.html" with btn_class="w-full h-11 min-h-11" %}</div>
      <span class="text-lead font-medium whitespace-nowrap tabular-nums shrink-0">{{ order.payable|toman }}</span>
    </div>
  </div>
{% endif %}{% endif %}

{% if can_manage and can_ship %}
  <div class="modal" popover id="ship-modal">
    <div class="modal-box max-w-sm">
      <h3 class="text-lead font-medium">ثبت ارسال</h3>
      <p class="text-small text-ink-2 mt-2">با ثبت ارسال، پیامک برای مشتری فرستاده می‌شود</p>
      <form method="post" action="{% url 'panel:order_status' order.number %}" hx-post="{% url 'panel:order_status' order.number %}"
            hx-target="#order-body" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']" class="mt-4 flex flex-col gap-3">
        {% csrf_token %}<input type="hidden" name="to" value="shipped">
        <fieldset class="fieldset">
          <legend class="fieldset-legend text-small font-medium">کد رهگیری{% if not needs_tracking %} (اختیاری){% endif %}</legend>
          <input type="text" name="tracking_code" maxlength="25" dir="ltr" autocomplete="off" autofocus{% if needs_tracking %} required{% endif %} class="input w-full text-end latin">
        </fieldset>
        <div class="flex items-center gap-2 border-t pt-3">
          <button type="submit" class="btn btn-primary flex-1 h-11 min-h-11">ثبت ارسال و ارسال پیامک</button>
          <button type="button" popovertarget="ship-modal" popovertargetaction="hide" class="btn btn-ghost h-11 text-ink-2">انصراف</button>
        </div>
      </form>
    </div>
  </div>
{% endif %}

{% if can_manage and can_cancel %}
  <div class="modal" popover id="cancel-modal">
    <div class="modal-box max-w-sm">
      <h3 class="text-lead font-medium">سفارش لغو شود؟</h3>
      <p class="text-small text-ink-2 mt-2 leading-6">موجودی کالاها به انبار برمی‌گردد و پیامک لغو برای مشتری ارسال می‌شود. اگر مشتری پرداخت کرده باشد، بازگشت وجه را جداگانه ثبت کنید</p>
      <form method="post" action="{% url 'panel:order_status' order.number %}" hx-post="{% url 'panel:order_status' order.number %}"
            hx-target="#order-body" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']" class="mt-4 flex flex-col gap-3">
        {% csrf_token %}<input type="hidden" name="to" value="cancelled">
        <fieldset class="fieldset">
          <legend class="fieldset-legend text-small font-medium">دلیل لغو</legend>
          <input type="text" name="note" maxlength="200" required autocomplete="off" autofocus class="input w-full">
        </fieldset>
        <div class="flex items-center gap-2 border-t pt-3">
          <button type="submit" class="btn btn-error flex-1 h-11 min-h-11">لغو سفارش</button>
          <button type="button" popovertarget="cancel-modal" popovertargetaction="hide" class="btn btn-ghost h-11 text-ink-2">انصراف</button>
        </div>
      </form>
    </div>
  </div>
{% endif %}

{% if can_refund %}
  {% for p in payments %}
    {% if p.pk in refund_ids or p.pk == refund_payment.pk %}
      {% include "panel/payments/_refund_modal.html" with payment=p next=request.path htmx_target="" %}
    {% endif %}
  {% endfor %}
{% endif %}

{% if request.htmx %}{% render_sidebar oob=True %}{% endif %}
```

#### پرداخت‌ها

`panel/payments/_refund_modal.html` (در جزئیات سفارش با POST معمولی، در فهرست پرداخت‌ها با HTMX):

```html
{% load core_tags %}
<div class="modal" popover id="refund-{{ payment.pk }}">
  <div class="modal-box max-w-md">
    <h3 class="text-lead font-medium">ثبت بازگشت وجه</h3>
    <p class="text-small text-ink-2 mt-2 leading-6">مبلغ <span class="font-medium whitespace-nowrap">{{ payment.amount|toman }} تومان</span> بابت سفارش <span class="latin">{{ payment.order.number }}</span>. ابتدا مبلغ را از پنل زرین‌پال به مشتری برگردانید؛ اینجا فقط ثبت می‌شود. اگر این پرداخت پشتوانه‌ی خود سفارش است، وضعیت سفارش هم «بازگشت وجه» می‌شود و پیامک می‌رود</p>
    <form method="post" action="{% url 'panel:payment_refund' payment.pk %}"
          {% if htmx_target %}hx-post="{% url 'panel:payment_refund' payment.pk %}" hx-target="{{ htmx_target }}" hx-swap="innerHTML" hx-disabled-elt="find button[type='submit']"{% endif %}
          class="mt-4 flex flex-col gap-3">
      {% csrf_token %}
      <input type="hidden" name="next" value="{{ next }}">
      {% for name, value in hidden %}<input type="hidden" name="{{ name }}" value="{{ value }}">{% endfor %}
      <label class="flex items-start gap-2 cursor-pointer">
        <input type="checkbox" name="confirm" value="1" required class="checkbox checkbox-sm mt-0.5">
        <span class="text-small">مبلغ را از پنل زرین‌پال برگردانده‌ام</span>
      </label>
      <fieldset class="fieldset">
        <legend class="fieldset-legend text-small font-medium">شماره‌ی پیگیری یا یادداشت</legend>
        <input type="text" name="note" maxlength="200" required autocomplete="off" class="input w-full">
      </fieldset>
      <div class="flex items-center gap-2 border-t pt-3">
        <button type="submit" class="btn btn-primary flex-1 h-11 min-h-11">ثبت بازگشت وجه</button>
        <button type="button" popovertarget="refund-{{ payment.pk }}" popovertargetaction="hide" class="btn btn-ghost h-11 text-ink-2">انصراف</button>
      </div>
    </form>
  </div>
</div>
```

`panel/payments/list.html`:

```html
{% extends "panel/shell.html" %}
{% load static %}
{% block title %}پرداخت‌ها{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="پرداخت‌ها" %}
    <span id="payments-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>

  <form action="{% url 'panel:payments' %}" method="get" role="search"
        hx-get="{% url 'panel:payments' %}" hx-target="#payments-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-sync="this:replace"
        hx-include="#payments-tab" hx-indicator="#payments-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3" data-date-range>
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ q }}" placeholder="شماره سفارش، شناسه‌ی مرجع یا شماره‌ی تراکنش" class="grow text-small" autocomplete="off">
    </label>
    <select name="gateway" class="select h-10 w-36 text-small">
      <option value="">همه‌ی درگاه‌ها</option>
      {% for code in gateways %}<option value="{{ code }}"{% if code == gateway %} selected{% endif %}>{{ code }}</option>{% endfor %}
    </select>
    <select name="status" class="select h-10 w-36 text-small">
      <option value="">همه‌ی وضعیت‌ها</option>
      {% for code, label in status_choices %}<option value="{{ code }}"{% if code == status %} selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <input type="text" name="from" value="{{ date_from }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="از تاریخ" class="input h-10 w-36 num text-small">
    <input type="text" name="to" value="{{ date_to }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="تا تاریخ" class="input h-10 w-36 num text-small">
    <span class="hidden text-label text-error" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد</span>
  </form>

  <div id="payments-results" aria-live="polite">{% include "panel/payments/_list_results.html" %}</div>
</div>
{% endblock %}
{% block extra_js %}<script src="{% static 'js/jalali_picker.js' %}" defer></script>{% endblock %}
```

`panel/payments/_list_results.html`:

```html
{% load core_tags jalali_tags panel_tags %}
<input type="hidden" id="payments-tab" name="tab" value="{{ tab }}">
<div class="flex flex-col gap-4">
  <div role="tablist" class="tabs tabs-border overflow-x-auto no-scrollbar">
    {% for code, label, count in tabs %}
      <a role="tab" class="tab gap-2 whitespace-nowrap{% if code == tab %} tab-active{% endif %}"
         href="?tab={{ code }}{% if filter_qs %}&{{ filter_qs }}{% endif %}"
         hx-get="?tab={{ code }}{% if filter_qs %}&{{ filter_qs }}{% endif %}" hx-target="#payments-results" hx-push-url="true"
         hx-indicator="#payments-indicator">
        {{ label }}<span class="text-label text-ink-3 num">{{ count|fa_digits }}</span>
      </a>
    {% endfor %}
  </div>

  {% if page_obj.object_list %}
    <div class="bg-base-100 border rounded-box overflow-x-auto">
      <table class="table table-sm">
        <thead><tr>
          <th scope="col">سفارش</th><th scope="col">درگاه</th><th scope="col">مبلغ (تومان)</th><th scope="col">وضعیت</th>
          <th scope="col">تراکنش</th><th scope="col">زمان</th><th scope="col"><span class="sr-only">اقدام</span></th>
        </tr></thead>
        <tbody>
          {% for p in page_obj.object_list %}
            <tr class="hover:bg-base-300">
              <td><a href="{% url 'panel:order_detail' p.order.number %}" class="latin link link-hover font-medium">{{ p.order.number }}</a></td>
              <td><span class="latin">{{ p.gateway_code }}</span></td>
              <td class="whitespace-nowrap">{{ p.amount|toman }}</td>
              <td><span class="flex items-center gap-2 text-small whitespace-nowrap"><span class="status {{ p.status|payment_dot }}"></span>{{ p.get_status_display }}</span></td>
              <td>{% if p.ref_id %}<span class="latin">{{ p.ref_id }}</span>{% endif %}{% if p.card_pan_masked %}<div class="latin text-label text-ink-3">{{ p.card_pan_masked }}</div>{% endif %}</td>
              <td class="text-ink-2 whitespace-nowrap"><span class="num">{{ p.created_at|to_jalali }}</span></td>
              <td>
                {% if can_refund and p.pk in candidate_ids %}
                  <button type="button" popovertarget="refund-{{ p.pk }}" class="btn btn-sm h-10 bg-base-300 border whitespace-nowrap">ثبت بازگشت وجه</button>
                  {% include "panel/payments/_refund_modal.html" with payment=p next=request.get_full_path htmx_target="#payments-results" %}
                {% endif %}
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% include "panel/partials/_pagination.html" with target="#payments-results" %}
  {% else %}
    {% include "partials/_empty_state.html" with title="پرداختی پیدا نشد" description="فیلترها را تغییر دهید یا تب دیگری را ببینید" %}
  {% endif %}
</div>
```

## ۵.۴ جاوااسکریپت، CSS و اسناد

**`static/js/mm/panel.js`** (جایگزین کامل؛ بدون `alert()`، D31):

```javascript
/* MM.panel: panel-only behaviour (docs/08-ui-modules.md): toast bridge, copy button, select-all, search panel. */
(function (MM) {
  "use strict";

  /* HX-Trigger: {"mm:toast": {"message": "...", "level": "success"}} */
  document.addEventListener("mm:toast", function (event) {
    var detail = event.detail || {};
    if (detail.message) MM.ui.toast(detail.message, { level: detail.level || "info" });
  });

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

**`static/src/input.css`:** این دو کلاس را اضافه کن (`06` بخش ۶.۱؛ تقویم شمسی به آن‌ها نیاز دارد). سند `06` ویرایش نمی‌شود:

```css
.fb-muted { color: color-mix(in oklab, var(--color-base-content) 60%, transparent); }
.font-technical { font-feature-settings: "tnum" 1; direction: ltr; unicode-bidi: isolate; }
```

بعد از آن `pnpm run build:css` اجرا و `static/css/app.css` commit شود.

**اسناد:**

- **`docs/08`:** ردیف `panel` از «برنامه‌ریزی‌شده» به قطعی تغییر کند، با سه مورد: پل toast، `[data-copy]` و `[data-check-all]`، و پنل جستجو. `[data-toman-hint]` و `[data-discount-from]` در همان ردیف ولی «P11» بمانند.
- **`docs/04` بخش ۹.۳:** استثنای «یک `btn-primary` در هر صفحه» برای مودال‌های `popover` (تا باز نشوند پنهان‌اند) هم نوشته شود.
- **`docs/09`:**
  - D42 به `[DECIDED]` تغییر کند.
  - بخش ۴ این بریف (تصمیم‌های ۱ تا ۶) در ماژول ۲ و ۳ ثبت شود.
  - `[OPEN]` شماره ۵ بسته شود.
  - ماژول ۳: «پرداخت تکراری یعنی وجود پرداخت قبلی `VERIFIED` یا `REFUNDED`».
- **`docs/02` تصمیم ۱۴ از P6:** همین اصلاح تعریف پرداخت تکراری.
- **`docs/deploy.md` بخش ۵ بند ۳:** مسیر رسیدگی «پنل ← پرداخت‌ها ← نیازمند بازگشت وجه ← ثبت بازگشت وجه» باشد، با اشاره به اینکه ادمین هم از همان سرویس می‌گذرد.
- **`STATUS.md`:** P9 «تمام‌شده با ترمیم در P10»، و P10 با خلاصه‌ی بالا.
- **`00-README.md` بخش ۸:** یک خط تغییر.
- **`setup_groups`:** در P10 تغییری ندارد. `engagement.view_stocksubscription` برای «فروش» فقط مصرف‌کننده‌ی P12 است، پس به P12 منتقل شد.

## ۵.۵ تست‌ها (فقط پول، مجوز و قاعده‌ی کسب‌وکار)

بودجه‌ی query، فیلتر UI، متن و مارک‌آپ تست نمی‌شوند. بودجه‌ی query در P15 «پاس عملکرد» است. «پنل `Order` را مستقیم تغییر نمی‌دهد» را هم `test_architecture` از قبل پوشش می‌دهد.

**`apps/panel/tests/conftest.py`:**

```python
import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User

PASSWORD = "Sup3r-Secret-pass"


@pytest.fixture
def staff_client(db):
    """A client logged in through /panel/login/ (so the panel session stamp exists), with exactly these permissions."""

    def make(*perms: str, mobile: str = "09129990100") -> Client:
        user = User.objects.create_user(mobile, password=PASSWORD, is_staff=True)
        for perm in perms:
            app, codename = perm.split(".")
            user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        client = Client()
        assert client.post(reverse("panel:login"), {"mobile": mobile, "password": PASSWORD}).status_code == 302
        return client

    return make
```

**`apps/panel/tests/test_access.py`:**

```python
"""The door: a forgotten decorator is the one panel bug that must never reach production."""

import pytest
from django.urls import reverse

from apps.panel import urls
from apps.orders.models import Order

pytestmark = pytest.mark.django_db


def test_every_panel_view_declares_its_access_rule():
    missing = [str(p.pattern) for p in urls.urlpatterns if not hasattr(p.callback, "panel_rule")]
    assert not missing, f"Add @panel_view(...) or @public_view: {missing}"


@pytest.mark.parametrize(
    ("name", "args"),
    [("panel:orders", []), ("panel:payments", []), ("panel:order_detail", ["ML-00000001"])],
)
def test_anonymous_goes_to_login_and_staff_without_the_permission_gets_403(client, staff_client, name, args):
    url = reverse(name, args=args)

    assert client.get(url)["Location"].startswith(reverse("panel:login"))
    assert staff_client("accounts.view_user").get(url).status_code == 403


def test_status_changes_need_the_manage_permission_and_go_through_the_workflow(staff_client, placed_order):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.PAID)  # tests may; the architecture scan skips them
    url = reverse("panel:order_status", args=[placed_order.number])

    viewer = staff_client("orders.view_order", mobile="09129990101")
    assert viewer.post(url, {"to": Order.PROCESSING}).status_code == 403

    manager = staff_client("orders.view_order", "orders.manage_order_status", mobile="09129990102")
    manager.post(url, {"to": Order.CANCELLED})  # no reason: refused
    placed_order.refresh_from_db()
    assert placed_order.status == Order.PAID

    manager.post(url, {"to": Order.CANCELLED, "note": "درخواست مشتری"})
    placed_order.refresh_from_db()
    assert placed_order.status == Order.CANCELLED
    assert placed_order.status_logs.get(to_status=Order.CANCELLED).by_user.mobile == "09129990102"
```

**`apps/panel/tests/test_queries.py`:**

```python
from datetime import date

import pytest

from apps.orders.models import Order
from apps.panel import queries

FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@pytest.mark.django_db
def test_order_search_finds_by_number_and_by_persian_mobile_fragment(placed_order):
    for text in (placed_order.number.lower(), placed_order.buyer_mobile[-6:].translate(FA)):
        assert Order.objects.filter(queries.order_search_q(text), pk=placed_order.pk).exists()


def test_the_end_day_of_a_range_is_included_and_a_reversed_range_is_swapped():
    low, high = queries.day_range("۱۴۰۵/۰۶/۳۰", "۱۴۰۵/۰۶/۲۹")  # 2026-09-21 and 2026-09-20

    assert (low.date(), high.date()) == (date(2026, 9, 20), date(2026, 9, 22))
```

**`apps/payments/tests/test_refund.py`:** پول، پس مهم‌ترین تست‌های فاز.

```python
import pytest

from apps.accounts.models import User
from apps.orders.models import Order
from apps.payments import services
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff():
    return User.objects.create_user("09129990200", password="x", is_staff=True)


@pytest.fixture
def paid(placed_order):
    return Payment.objects.create(order=placed_order, gateway_code="fake", amount=placed_order.payable, status=Payment.VERIFIED)


def test_refund_on_a_cancelled_order_closes_the_payment_and_the_order_once(placed_order, paid, staff):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.CANCELLED)

    result = services.record_refund(paid.pk, by=staff, note="پیگیری ۱۲۳")

    placed_order.refresh_from_db()
    assert (result.order_refunded, placed_order.status) == (True, Order.REFUNDED)
    assert Payment.objects.get(pk=paid.pk).status == Payment.REFUNDED
    assert placed_order.status_logs.filter(to_status=Order.REFUNDED, by_user=staff).count() == 1
    with pytest.raises(services.RefundError):  # a second click must not refund again
        services.record_refund(paid.pk, by=staff, note="دوباره")


def test_refund_is_refused_without_a_note_and_for_an_order_still_in_progress(placed_order, paid, staff):
    with pytest.raises(services.RefundError):
        services.record_refund(paid.pk, by=staff, note="  ")
    with pytest.raises(services.RefundError):  # the order is still pending_payment
        services.record_refund(paid.pk, by=staff, note="x")
    assert Payment.objects.get(pk=paid.pk).status == Payment.VERIFIED


def test_a_second_verified_payment_is_refunded_without_touching_the_order(placed_order, paid, staff):
    Order.objects.filter(pk=placed_order.pk).update(status=Order.PAID)
    duplicate = Payment.objects.create(order=placed_order, gateway_code="fake", amount=1, status=Payment.VERIFIED)
    assert list(services.refund_candidates()) == [duplicate]

    result = services.record_refund(duplicate.pk, by=staff, note="تکراری")

    placed_order.refresh_from_db()
    assert (result.order_refunded, placed_order.status) == (False, Order.PAID)
    Payment.objects.filter(pk=paid.pk).update(status=Payment.REFUNDED)  # the first one is refunded elsewhere
    other = Payment.objects.create(order=placed_order, gateway_code="fake", amount=1, status=Payment.VERIFIED)
    assert other in services.refund_candidates()  # a refunded payment still makes the next one a duplicate
```

**تست‌های موجود که حذف می‌شوند** (مارک‌آپ یا رفتار خود فریم‌ورک، `CLAUDE.md` بخش ۶):

- `apps/accounts/tests/test_profile.py::TestProfilePage::test_get_shows_the_locked_national_code`: فقط `"readonly"`، `"bg-base-300"` و ... را در HTML می‌شمارد. قفل کد ملی جای دیگری تست می‌شود و نمایش ارقام فارسی را `test_persian_digits` پوشش می‌دهد.
- `apps/accounts/tests/test_login_views.py::TestSessions::test_profile_requires_login`: تکرار `TestAddressList::test_requires_login` و فقط `@login_required`.
- `apps/core/tests/test_core_app.py::TestCoreModelsAndViews::test_home_has_no_external_cdn_and_inactive_pages_are_404`: grep روی یک صفحه و رفتار `get_object_or_404`. پس از حذف، `StaticPage` از import همان فایل هم برداشته شود (ruff F401).

> خروجی اجرای تست‌ها در دسترس نبود، پس فقط مواردی حذف شده‌اند که از روی کد بدون ابهام «مارک‌آپ یا فریم‌ورک» بودند.

## ۶. Definition of Done

- [ ] `uv run python manage.py check` بدون خطا و `scripts/build_sprite.py` با کد خروج صفر (نقص‌های بخش ۱ برطرف شده‌اند).
- [ ] `uv run pytest` و `uv run ruff check .` و `uv run ruff format .` بدون خطا (خروجی خوانده شود).
- [ ] grepهای `04` بخش ۱۳ روی `templates/` و `static/src/` صفر نتیجه می‌دهند.
- [ ] `pnpm run build:css` اجرا شده و `static/css/app.css` commit شده است.
- [ ] `record_refund` تنها راه `REFUNDED` شدن پرداخت است. اکشن ادمین از آن می‌گذرد و فرم وضعیت ادمین گزینه‌ی «بازگشت وجه» ندارد.
- [ ] `[OPEN]` چاپ دسته‌جمعی فاکتور از کاربر پرسیده شده و جوابش (یا «ساخته نشد») در `docs/09` ثبت شده است.
- [ ] `[VERIFY]` لینک نقشه با `docs/vendors/neshan/` تطبیق داده شده و نتیجه (OSM یا لینک مستند) در گزارش آمده است.
- [ ] اسناد بخش ۵.۴ و `STATUS.md` به‌روز است.

## ۷. فهرست بررسی چشمی (با کاربر؛ Claude Code مرورگر یا Playwright اجرا نمی‌کند)

هر مورد در دو تم و در عرض‌های ۳۲۰ و ۱۲۸۰ دیده شود.

- **ورود:** رمز اشتباه پیام یکسان می‌دهد. ورود درست به داشبورد می‌رود و حلقه‌ی ریدایرکت ندارد.
- **سایدبار:** آیتم فعال مشخص است. بج‌ها با صفر جا را نگه می‌دارند و چیزی نمی‌پرد. در موبایل کشو باز و بسته می‌شود.
- **جستجوی بالا:** با «ML-» یا چهار رقم موبایل (فارسی هم) نتیجه می‌آید و با کلیک بیرون بسته می‌شود.
- **داشبورد:** دو کارت، صف ارسال و هشدار بازگشت وجه. «شروع آماده‌سازی» از صف ردیف را تازه می‌کند و toast می‌آید.
- **فهرست سفارش:**
  - تب‌ها با شمارنده عوض می‌شوند و آدرس مرورگر هم عوض می‌شود.
  - تقویم شمسی باز می‌شود، «پاک‌کردن» نتیجه را تازه می‌کند و بازه‌ی برعکس پیام خطا می‌دهد.
  - انتخاب همه و «شروع آماده‌سازی انتخاب‌شده‌ها» در دسکتاپ کار می‌کند.
  - در موبایل کارت دیده می‌شود، نه جدول.
- **جزئیات سفارش:**
  - نوار مراحل درست است.
  - مودال ارسال کد رهگیری می‌خواهد.
  - مودال لغو بدون دلیل ثبت نمی‌شود.
  - بعد از هر تغییر، ردیف تاریخچه اضافه می‌شود و بج سایدبار تازه می‌شود.
  - در موبایل دکمه‌ی اصلی در نوار چسبان پایین و سمت راست است و مبلغ سمت چپ.
  - «کپی مشخصات» toast می‌دهد.
  - فاکتور در تب جدید باز می‌شود.
  - ارسال دوباره‌ی پیامک پیام می‌دهد.
- **پرداخت‌ها:** تب بازگشت وجه، مودال با چک‌باکس و یادداشت اجباری، و ناپدید شدن ردیف بعد از ثبت. ثبت از صفحه‌ی سفارش هم کار می‌کند و به همان صفحه برمی‌گردد.
- **کلی:** ارقام فارسی، آیکون‌های جهت‌دار برعکس، و یک `btn-primary` در هر صفحه (به‌جز مودال‌ها).
