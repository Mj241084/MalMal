# فاز P14: مشتریان، تنظیمات و سیستم

**هدف:** بخش‌های مدیریتی پنل کامل شود: مشتریان، تنظیمات، پیامک، همکاران، ممیزی و آمادگی انتشار. بعد از این فاز، کار مدیر کل بدون ادمین جنگو انجام می‌شود.

---

## ۰. قواعد این نشست (سخت‌گیرانه)

- فقط فایل‌هایی را که در این بریف نام برده شده می‌خوانی و تغییر می‌دهی. اسکیل اجرا نکن، وب نگرد، فایل اضافه نخوان. فقط دستورهای فهرست‌شده در گام ۰ و گام ۹ مجازند.
- **بررسی چشمی را خودت انجام نمی‌دهی.** مرورگر، Playwright و اسکرین‌شات ممنوع است. فقط «فهرست بررسی چشمی» پایین را در گزارش آخر به من بده.
- **تست‌ها فقط دو بار اجرا می‌شوند:** گام ۰ و گام ۹. وسط کار تست اجرا نکن.
- خطای `unable to open database file` مشکل محیط (قفل یا مسیر موقت ویندوز) است، نه کد. وقتی دیدی دنبال علتش نگرد. فقط با `TEMP`/`TMP` داخل پروژه اجرا کن (دستور در گام ۰). اگر باز هم آمد، همان را گزارش کن و ادامه بده.
- اگر تستی شکست خورد:
  - اگر تقصیر کد همین فاز بود، خودت درستش کن.
  - اگر به کد قدیمی مربوط بود، فقط شکست را با نام تست و خطا گزارش بده و منتظر تایید من بمان. بدون تایید چیزی را برای رفع آن تغییر نده.
- تستی غیر از تست‌های همین بریف ننویس. پوشه‌ی `tests` را نگرد. فقط برای نوشتن تست‌ها، یک نگاه به نزدیک‌ترین فایل تست پنل (`apps/panel/tests/`) برای یافتن helper ورود کارمند کافی است.
- `[OPEN]` سوال ۴ (`09` بخش ۲.۱۰: آیا گروه چهارم، مثلاً «مدیر فروشگاه» بدون superuser، لازم است؟) کار را نگه نمی‌دارد. هیچ کدی به آن وابسته نیست، چون گروه‌ها از دیتابیس خوانده می‌شوند. در گزارش آخر یک‌خطی از من بپرس و جوابم را در `09` ثبت کن.

## مطالعه (فقط این‌ها)

`CLAUDE.md`، این بریف، و فایل‌هایی که ویرایش می‌شوند: `apps/accounts/{services.py,management/commands/create_staff.py,management/commands/setup_groups.py}`، `apps/core/management/commands/check_launch.py`، `apps/panel/{nav.py,urls.py,providers.py,queries.py,templatetags/panel_tags.py}`، `apps/panel/views/common.py`، `apps/panel/forms_marketing.py` (کلاس `PanelForm`). برای هر قالب جدید الگو همان قالب‌های موجود پنل است. از `docs/09` فقط ماژول‌های ۱۱ تا ۱۴ و بخش ۲.۵.

---

## گام ۰: وضعیت پایه

```powershell
$env:TEMP="$PWD\.tmp"; $env:TMP="$PWD\.tmp"; $env:UV_CACHE_DIR="$PWD\.uv-cache"
uv run pytest -q
```

نام تست‌های شکست‌خورده را یادداشت کن (خط پایه). بعد از گام ۹ همین دستور را دوباره اجرا و با خط پایه مقایسه می‌کنی.

---

## تصمیم‌های این فاز

| # | تصمیم |
|---|-------|
| 1 | گزارش پیامک در `/panel/sms/` است، نه `/panel/system/sms/`. چون نقش‌های غیر superuser هم می‌توانند `notifications.view_smslog` بگیرند، و ناوبری با پیشوند مسیر فعال را تشخیص می‌دهد (وگرنه «سیستم» و «پیامک» هم‌زمان روشن می‌شدند). |
| 2 | `ShippingMethod.payment_mode` در رابط **فقط‌خواندنی** است. `place_order` همیشه `shipping_cost=0` می‌گذارد و حالت `prepaid` خلاف واقع نشان می‌دهد. این انحراف آگاهانه از `09` ماژول ۱۲ است و باید در سند ثبت شود. |
| 3 | مدیر کل (superuser) از پنل ساخته نمی‌شود و گروه و رمزش از پنل ویرایش نمی‌شود (D47). فقط می‌شود فعال/غیرفعالش کرد (به‌جز خودت و آخرین مدیر کل فعال). |
| 4 | ساخت همکار از شماره‌ی موجود (حتی همکار) در پنل رد می‌شود. دستور `create_staff` رفتار قبلی را حفظ می‌کند (رمز و گروه همکار موجود را به‌روز می‌کند). |
| 5 | لوگو از پنل فقط jpg/png/webp تا ۲ مگابایت. SVG از ادمین. |
| 6 | درگاه: غیرفعال‌کردن آخرین درگاه قابل‌استفاده فقط با تیک تایید خطرناک انجام می‌شود. |
| 7 | بدون تغییر مدل و مهاجرت. |
| 8 | provider جستجو و بج سفارش/محصول/بازگشت وجه در `providers.py` ثبت نیست (فقط بج نظرها). این‌ها به P15 موکول‌اند و **در این فاز دست نزن**. فقط provider مشتریان اضافه می‌شود. |

---

## گام ۱: سرویس‌های `accounts`

**`apps/accounts/services.py`**: imports را کامل کن و کد زیر را به انتهای فایل (بعد از `save_new_address`) اضافه کن.

```python
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.accounts.models import Address, User
from apps.core.validators import normalize_iran_mobile, validate_national_code
```

```python
# --- staff (docs/09 module 13, D47) ---------------------------------------

STAFF_ERRORS = {
    "customer": "این شماره‌ی یک مشتری است (ورود با کد پیامکی)؛ برای همکار شماره‌ی جدا لازم است",
    "exists": "این شماره قبلاً به‌عنوان همکار ثبت شده؛ از فهرست همکاران ویرایشش کنید",
    "group": "گروه نامعتبر است؛ ابتدا setup_groups را اجرا کنید",
    "self": "حساب خودتان را نمی‌توانید غیرفعال کنید",
    "last_superuser": "آخرین مدیر کل فعال را نمی‌توان غیرفعال کرد",
    "superuser": "حساب مدیر کل از پنل ویرایش نمی‌شود",
    "not_staff": "این حساب همکار نیست",
}


class StaffError(Exception):
    """A refusal whose message is safe to show. `code` lets callers (the management command) pick their own text."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or STAFF_ERRORS[code])
        self.code = code


def _groups(names) -> list[Group]:
    names = list(names)
    groups = list(Group.objects.filter(name__in=names))
    if len(groups) != len(set(names)):
        raise StaffError("group")
    return groups


def prepare_staff(mobile: str, group_names, *, allow_existing: bool = True):
    """The checks that do not need a password. Returns (normalized mobile, existing user or None, groups)."""
    try:
        mobile = normalize_iran_mobile(mobile)
    except ValidationError as exc:
        raise StaffError("mobile", exc.messages[0]) from exc
    user = User.objects.filter(mobile=mobile).first()
    if user is not None and not user.is_staff:
        raise StaffError("customer")
    if user is not None and not allow_existing:
        raise StaffError("exists")
    return mobile, user, _groups(group_names)


def create_staff_user(
    mobile: str,
    password: str,
    group_names=(),
    *,
    first_name: str = "",
    last_name: str = "",
    allow_existing: bool = True,
) -> User:
    """Create a staff account (never a superuser). An existing staff number gets the new password and groups."""
    mobile, user, groups = prepare_staff(mobile, group_names, allow_existing=allow_existing)
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise StaffError("password", " ".join(exc.messages)) from exc
    with transaction.atomic():
        if user is None:
            user = User.objects.create_user(
                mobile, password=password, is_staff=True, first_name=first_name, last_name=last_name
            )
        else:
            user.set_password(password)
            user.save()
        user.groups.set(groups)
    return user


def _editable_staff(target: User) -> None:
    if not target.is_staff:
        raise StaffError("not_staff")
    if target.is_superuser:
        raise StaffError("superuser")


def update_staff_profile(target: User, *, first_name: str, last_name: str, group_names) -> None:
    _editable_staff(target)
    groups = _groups(group_names)
    with transaction.atomic():
        target.first_name, target.last_name = first_name, last_name
        target.save(update_fields=["first_name", "last_name"])
        target.groups.set(groups)


def reset_staff_password(target: User, password: str) -> None:
    """New password; every session of that person ends (session_version + 1)."""
    _editable_staff(target)
    try:
        validate_password(password, target)
    except ValidationError as exc:
        raise StaffError("password", " ".join(exc.messages)) from exc
    target.set_password(password)
    target.session_version += 1
    target.save(update_fields=["password", "session_version"])


def set_staff_active(target: User, *, by: User, active: bool) -> None:
    if not target.is_staff:
        raise StaffError("not_staff")
    if not active:
        if target.pk == by.pk:
            raise StaffError("self")
        others = User.objects.filter(is_staff=True, is_superuser=True, is_active=True).exclude(pk=target.pk)
        if target.is_superuser and not others.exists():
            raise StaffError("last_superuser")
    if target.is_active != active:
        target.is_active = active  # the session hash includes is_active: an inactive person's sessions stop working
        target.save(update_fields=["is_active"])


# --- customers (docs/09 module 11, D20) ------------------------------------


class CustomerError(Exception):
    """A refusal whose message is safe to show to staff."""


def _customer(user: User) -> None:
    if user.is_staff:
        raise CustomerError("حساب همکار از این بخش ویرایش نمی‌شود")


def change_national_code(user: User, raw_code: str) -> str:
    """Open the D20 lock for one validated change. The view checks the permission and writes the audit entry.

    Returns the previous code.
    """
    _customer(user)
    try:
        code = validate_national_code(raw_code)
    except ValidationError as exc:
        raise CustomerError(exc.messages[0]) from exc
    previous = user.national_code
    if code == previous:
        raise CustomerError("کد ملی تازه با کد فعلی یکی است")
    with transaction.atomic():
        user.allow_national_code_change()
        user.national_code = code
        user.save(update_fields=["national_code"])
    return previous


def set_customer_active(user: User, active: bool) -> None:
    _customer(user)
    if user.is_active != active:
        user.is_active = active
        user.save(update_fields=["is_active"])


def revoke_sessions(user: User) -> None:
    User.objects.filter(pk=user.pk).update(session_version=F("session_version") + 1)
```

اگر بعضی importها از قبل در فایل هست، تکراری نیاور (ruff `I001` را اجرا می‌کند).

**`apps/accounts/management/commands/create_staff.py`**: کل فایل را با این جایگزین کن. خروجی و پیام‌ها و ترتیب خطاها مثل قبل می‌ماند.

```python
"""Create a staff account that logs in to the admin with a password (customers use OTP only)."""

import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import services

ENGLISH = {
    "customer": "This mobile belongs to a customer (OTP login); staff need their own number.",
    "group": "Unknown group; run `manage.py setup_groups` first.",
}


class Command(BaseCommand):
    help = "create_staff 0912... --group محتوا --group فروش"

    def add_arguments(self, parser):
        parser.add_argument("mobile")
        parser.add_argument("--group", action="append", default=[])

    def handle(self, *args, mobile, group, **options):
        try:
            services.prepare_staff(mobile, group)
        except services.StaffError as exc:
            raise CommandError(ENGLISH.get(exc.code, str(exc))) from exc

        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Again: "):
            raise CommandError("Passwords differ.")
        try:
            user = services.create_staff_user(mobile, password, group)
        except services.StaffError as exc:
            raise CommandError(ENGLISH.get(exc.code, str(exc))) from exc
        self.stdout.write(self.style.SUCCESS(f"Staff {user.mobile} ready ({', '.join(group) or 'no group'})."))
```

**`apps/accounts/management/commands/setup_groups.py`**: اگر در `GROUPS["فروش"]` ردیف زیر نیست، اضافه کن (دیگر چیزی عوض نمی‌شود):

```python
(("accounts", ("user",), VIEW),)
```

---

## گام ۲: `check_launch.collect_detailed`

**`apps/core/management/commands/check_launch.py`**: بعد از تابع `collect()` اضافه کن. `collect()` و `Command` دست‌نخورده می‌مانند.

```python
# finding text -> panel url name where it can be fixed (anything else is an .env or server task)
_FIXES = (
    ("هیچ درگاه واقعی", "panel:gateway_list"),
    ("روش ارسال فعالی", "panel:shipping_list"),
    ("صفحه‌ی ثابت فعال", "panel:pages"),
    ("نیازمند بازبینی", "panel:pages"),
    ("تنظیمات سایت", "panel:settings_identity"),
    ("لوگوی نهایی", "panel:settings_identity"),
    ("نماد اعتماد", "panel:settings_advanced"),
    ("بازگشت وجه", "panel:payments"),
)


def collect_detailed():
    """collect() plus the panel page that fixes each finding ('' when it is an .env or server task)."""
    for level, text in collect():
        yield level, text, next((name for needle, name in _FIXES if needle in text), "")
```

---

## گام ۳: پرس‌وجوها، provider جستجو و فیلتر قالب

**`apps/panel/queries.py`**: به importها اضافه کن: `from pathlib import Path` و `from django.conf import settings`. به انتهای فایل اضافه کن:

```python
# --- Phase 14 helpers --------------------------------------------------------


def customer_search_q(raw: str) -> Q | None:
    """Name, or (part of) a mobile number or national code; Persian digits are fine."""
    text = normalize_fa(raw)[:40].strip()
    if not text:
        return None
    condition = Q(first_name__icontains=text) | Q(last_name__icontains=text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 3:
        condition |= Q(mobile__contains=digits) | Q(national_code__contains=digits)
    return condition


def backup_status() -> dict | None:
    """Newest db-*.sqlite3 in BACKUP_DIR. None when BACKUP_DIR is unset or missing; empty name when no copy exists."""
    if not settings.BACKUP_DIR:
        return None
    folder = Path(settings.BACKUP_DIR)
    if not folder.is_dir():
        return None
    files = sorted(folder.glob("db-*.sqlite3"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        return {"name": "", "at": None, "stale": True}
    moment = datetime.fromtimestamp(files[0].stat().st_mtime, tz=timezone.get_current_timezone())
    return {"name": files[0].name, "at": moment, "stale": timezone.now() - moment > timedelta(days=2)}
```

**`apps/panel/providers.py`**: کل فایل:

```python
from django.urls import reverse

from apps.accounts.models import User
from apps.panel import badges, queries, search


@badges.register("reviews_pending")
def reviews_pending() -> int:
    return queries.reviews_pending()


@search.register("customers", "مشتریان", "accounts.view_user")
def customers_search(query: str) -> list[search.Hit]:
    condition = queries.customer_search_q(query)
    if condition is None:
        return []
    rows = User.objects.filter(is_staff=False).filter(condition).order_by("-date_joined")[: search.PER_PROVIDER]
    return [
        search.Hit(
            title=user.get_full_name() or user.mobile,
            subtitle=user.mobile,
            url=reverse("panel:customer_detail", args=[user.pk]),
        )
        for user in rows
    ]
```

**`apps/panel/templatetags/panel_tags.py`**: `from apps.notifications.models import SmsLog` را import کن و اضافه کن:

```python
SMS_DOT = {
    SmsLog.STATUS_SENT: "status-success",
    SmsLog.STATUS_FAILED: "status-error",
    SmsLog.STATUS_SKIPPED_NO_TEMPLATE: "status-warning",
}


@register.filter
def sms_dot(status: str) -> str:
    return SMS_DOT.get(status, "status-neutral")
```

---

## گام ۴: فرم‌ها: `apps/panel/forms_settings.py` (فایل جدید)

```python
"""Settings, shipping, gateway, staff and national-code forms of the panel (docs/09 modules 11 to 13)."""

from __future__ import annotations

from django import forms
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import UploadedFile

from apps.catalog.images import validate_upload
from apps.core.forms import FieldErrorAttrsMixin
from apps.core.models import SiteSettings
from apps.core.text import normalize_digits, normalize_fa
from apps.core.validators import normalize_iran_mobile, normalize_national_code, validate_national_code
from apps.core.widgets import FaDigitsInput, FaTextarea, FaTextInput
from apps.orders.models import ShippingMethod
from apps.panel.fields import FaIntegerField, TomanField
from apps.panel.forms_marketing import PanelForm
from apps.payments import gateways
from apps.payments.models import PaymentGateway

LOGO_MAX_BYTES = 2 * 1024 * 1024
FILE = {"accept": "image/png,image/jpeg,image/webp"}
LOGO_HELP = "jpg، png یا webp، حداکثر ۲ مگابایت"


def first_error(form) -> str:
    for errors in form.errors.values():
        return str(errors[0])
    return "اطلاعات را بررسی کنید"


class _LogoMixin:
    def _checked_logo(self, name: str):
        file = self.cleaned_data.get(name)
        if isinstance(file, UploadedFile):
            validate_upload(file, max_bytes=LOGO_MAX_BYTES, label="لوگو")
        return file


# --- site settings (one form per tab) ---------------------------------------


class IdentityForm(_LogoMixin, PanelForm):
    normalized = ("store_name", "address", "working_hours")
    field_order = [
        "store_name", "phone", "email", "address", "working_hours", "instagram_url", "telegram_url",
        "whatsapp_url", "logo_light", "logo_light_clear", "logo_dark", "logo_dark_clear",
    ]  # fmt: skip
    logo_light_clear = forms.BooleanField(required=False, label="حذف لوگوی روشن فعلی")
    logo_dark_clear = forms.BooleanField(required=False, label="حذف لوگوی تاریک فعلی")

    class Meta:
        model = SiteSettings
        fields = [
            "store_name", "phone", "email", "address", "working_hours", "instagram_url", "telegram_url",
            "whatsapp_url", "logo_light", "logo_dark",
        ]  # fmt: skip
        labels = {
            "store_name": "نام فروشگاه",
            "phone": "تلفن",
            "email": "ایمیل",
            "address": "آدرس",
            "working_hours": "ساعات پاسخگویی",
            "instagram_url": "اینستاگرام",
            "telegram_url": "تلگرام",
            "whatsapp_url": "واتساپ",
            "logo_light": "لوگوی تم روشن",
            "logo_dark": "لوگوی تم تاریک",
        }
        help_texts = {"logo_light": LOGO_HELP, "logo_dark": LOGO_HELP}
        widgets = {
            "store_name": FaTextInput(),
            "phone": FaDigitsInput(attrs={"autocomplete": "tel"}),
            "address": FaTextarea(attrs={"rows": 3}),
            "working_hours": FaTextInput(),
            "logo_light": forms.FileInput(attrs=FILE),
            "logo_dark": forms.FileInput(attrs=FILE),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("logo_light", "logo_dark"):
            self.fields[name].widget.attrs["data-preview"] = f"#preview-{name}"

    def clean_phone(self) -> str:
        return normalize_digits(self.cleaned_data["phone"]).strip()  # tel: links need ASCII

    def clean_email(self) -> str:
        return (self.cleaned_data["email"] or "").strip().lower()

    def clean_logo_light(self):
        return self._checked_logo("logo_light")

    def clean_logo_dark(self):
        return self._checked_logo("logo_dark")


class LegalForm(PanelForm):
    normalized = ("legal_name", "legal_address")
    ASCII = ("economic_code", "national_id", "registration_no", "legal_postal_code", "legal_phone")

    class Meta:
        model = SiteSettings
        fields = [
            "legal_name", "economic_code", "national_id", "registration_no", "legal_address",
            "legal_postal_code", "legal_phone",
        ]  # fmt: skip
        labels = {
            "legal_name": "نام حقوقی / فروشنده",
            "economic_code": "کد اقتصادی",
            "national_id": "شناسه‌ی ملی",
            "registration_no": "شماره‌ی ثبت",
            "legal_address": "آدرس حقوقی",
            "legal_postal_code": "کدپستی فروشنده",
            "legal_phone": "تلفن فاکتور",
        }
        help_texts = {"legal_name": "فاکتور فیلد خالی را نشان نمی‌دهد"}
        widgets = {
            "legal_name": FaTextInput(),
            "economic_code": FaDigitsInput(),
            "national_id": FaDigitsInput(),
            "registration_no": FaDigitsInput(),
            "legal_address": FaTextarea(attrs={"rows": 3}),
            "legal_postal_code": FaDigitsInput(),
            "legal_phone": FaDigitsInput(),
        }

    def clean(self):
        cleaned = super().clean()
        for name in self.ASCII:  # the invoice prints these as Latin codes (.latin) or runs fa_digits over them
            if isinstance(cleaned.get(name), str):
                cleaned[name] = normalize_digits(cleaned[name]).strip()
        return cleaned


class SalesForm(PanelForm):
    normalized = ("shipping_note",)
    low_stock_threshold = FaIntegerField(label="آستانه‌ی هشدار موجودی کم", min_value=0, max_value=1000)
    back_in_stock_start_hour = FaIntegerField(
        label="شروع ساعت ارسال «موجود شد»", min_value=0, max_value=23, help_text="ساعت ۰ تا ۲۳ به وقت تهران"
    )
    back_in_stock_end_hour = FaIntegerField(label="پایان ساعت ارسال «موجود شد»", min_value=1, max_value=24)

    class Meta:
        model = SiteSettings
        fields = ["low_stock_threshold", "back_in_stock_start_hour", "back_in_stock_end_hour", "shipping_note"]
        labels = {"shipping_note": "متن ارسال در صفحه‌ی محصول"}
        help_texts = {"shipping_note": "جایگزین وقتی روش ارسال فعال متنی ندارد. خالی = نمایش داده نمی‌شود"}
        widgets = {"shipping_note": FaTextInput()}

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("back_in_stock_start_hour"), cleaned.get("back_in_stock_end_hour")
        if start is not None and end is not None and start >= end:
            self.add_error("back_in_stock_end_hour", "پایان باید بعد از شروع باشد")
        return cleaned


class AdvancedForm(PanelForm):
    """Superuser only: OTP rules and the trust-marks HTML (rendered unescaped in the footer)."""

    otp_ttl_seconds = FaIntegerField(label="مدت اعتبار کد تایید (ثانیه)", min_value=30, max_value=600)
    otp_max_attempts = FaIntegerField(label="حداکثر تلاش کد تایید", min_value=1, max_value=10)
    otp_lock_minutes = FaIntegerField(label="مدت قفل پس از خطا (دقیقه)", min_value=1, max_value=120)

    class Meta:
        model = SiteSettings
        fields = ["otp_ttl_seconds", "otp_max_attempts", "otp_lock_minutes", "trust_marks_html"]
        labels = {"trust_marks_html": "کد HTML نمادهای اعتماد"}
        help_texts = {
            "trust_marks_html": "بدون پاک‌سازی در فوتر نمایش داده می‌شود؛ فقط کد معتبر نماد (مثل اینماد) بگذارید"
        }
        widgets = {"trust_marks_html": forms.Textarea(attrs={"rows": 5, "dir": "ltr"})}


# --- shipping methods and gateways -----------------------------------------


class ShippingMethodForm(PanelForm):
    normalized = ("title", "product_note", "checkout_note")
    sort = FaIntegerField(label="ترتیب", min_value=0, max_value=9999)

    class Meta:
        model = ShippingMethod
        fields = ["title", "product_note", "checkout_note", "has_tracking", "payment_mode", "is_active", "sort"]
        labels = {
            "title": "عنوان",
            "product_note": "متن صفحه‌ی محصول",
            "checkout_note": "متن checkout",
            "has_tracking": "با کد رهگیری",
            "payment_mode": "نحوه‌ی پرداخت کرایه",
            "is_active": "فعال",
        }
        widgets = {"title": FaTextInput(), "product_note": FaTextInput(), "checkout_note": FaTextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["payment_mode"]
        field.disabled = True  # v1: shipping_cost is always 0 (collect mode), so another mode would mislead
        field.help_text = "در نسخه‌ی ۱ فقط پس‌کرایه است"

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.is_active and not cleaned.get("is_active"):
            others = ShippingMethod.objects.filter(is_active=True).exclude(pk=self.instance.pk)
            if not others.exists():
                self.add_error("is_active", "آخرین روش ارسال فعال را نمی‌توان غیرفعال کرد؛ checkout از کار می‌افتد")
        return cleaned


class GatewayForm(_LogoMixin, PanelForm):
    normalized = ("title",)
    field_order = ["title", "logo", "logo_clear", "is_active", "confirm_last", "sort", "min_amount", "max_amount"]
    sort = FaIntegerField(label="ترتیب", min_value=0, max_value=9999)
    min_amount = TomanField(label="حداقل مبلغ (تومان)")
    max_amount = TomanField(label="حداکثر مبلغ (تومان)", required=False, help_text="خالی = بدون سقف")
    logo_clear = forms.BooleanField(required=False, label="حذف لوگوی فعلی")
    confirm_last = forms.BooleanField(
        required=False,
        label="می‌دانم با غیرفعال‌شدن این درگاه پرداخت آنلاین بسته می‌شود",
        help_text="فقط وقتی آخرین درگاه قابل‌استفاده را غیرفعال می‌کنید لازم است",
    )

    class Meta:
        model = PaymentGateway
        fields = ["title", "logo", "is_active", "sort", "min_amount", "max_amount"]
        labels = {"title": "عنوان", "logo": "لوگو", "is_active": "فعال"}
        help_texts = {"logo": LOGO_HELP}
        widgets = {"title": FaTextInput(), "logo": forms.FileInput(attrs=FILE)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].widget.attrs["data-preview"] = "#preview-logo"

    def clean_logo(self):
        return self._checked_logo("logo")

    def clean_max_amount(self):
        return self.cleaned_data.get("max_amount") or None

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_amount"), cleaned.get("max_amount")
        if low is not None and high is not None and low > high:
            self.add_error("max_amount", "حداکثر نباید کمتر از حداقل باشد")
        if self.instance.pk and self.instance.is_active and not cleaned.get("is_active"):
            if not any(g.pk != self.instance.pk for g in gateways.available()) and not cleaned.get("confirm_last"):
                self.add_error("confirm_last", "این آخرین درگاه قابل‌استفاده است؛ برای ادامه تیک تایید را بزنید")
        return cleaned


# --- staff ------------------------------------------------------------------


class StaffForm(FieldErrorAttrsMixin, forms.Form):
    first_name = forms.CharField(
        label="نام", required=False, max_length=80, widget=FaTextInput(attrs={"class": "input w-full"})
    )
    last_name = forms.CharField(
        label="نام خانوادگی", required=False, max_length=80, widget=FaTextInput(attrs={"class": "input w-full"})
    )
    groups = forms.ModelMultipleChoiceField(
        label="گروه‌ها", queryset=Group.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.order_by("name")

    def clean_first_name(self) -> str:
        return normalize_fa(self.cleaned_data["first_name"])

    def clean_last_name(self) -> str:
        return normalize_fa(self.cleaned_data["last_name"])


class StaffCreateForm(StaffForm):
    field_order = ["mobile", "first_name", "last_name", "groups", "password1", "password2"]
    mobile = forms.CharField(
        label="موبایل", max_length=20, widget=FaDigitsInput(attrs={"class": "input w-full text-end num"})
    )
    password1 = forms.CharField(
        label="رمز موقت",
        help_text="همکار می‌تواند بعد از ورود در «حساب من» عوضش کند",
        widget=forms.PasswordInput(attrs={"class": "input w-full", "dir": "ltr", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="تکرار رمز",
        widget=forms.PasswordInput(attrs={"class": "input w-full", "dir": "ltr", "autocomplete": "new-password"}),
    )

    def clean_mobile(self) -> str:
        return normalize_iran_mobile(self.cleaned_data["mobile"])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "رمزها مطابقت ندارند")
        return cleaned


class StaffPasswordForm(FieldErrorAttrsMixin, forms.Form):
    password1 = forms.CharField(
        label="رمز تازه",
        widget=forms.PasswordInput(attrs={"class": "input w-full", "dir": "ltr", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="تکرار رمز تازه",
        widget=forms.PasswordInput(attrs={"class": "input w-full", "dir": "ltr", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "رمزها مطابقت ندارند")
        return cleaned


# --- customers --------------------------------------------------------------


class NationalCodeForm(FieldErrorAttrsMixin, forms.Form):
    code = forms.CharField(
        label="کد ملی تازه",
        max_length=10,
        widget=FaDigitsInput(attrs={"class": "input w-full text-end num", "maxlength": "10", "data-digits-only": "1"}),
    )
    note = forms.CharField(
        label="دلیل تغییر",
        max_length=200,
        widget=FaTextInput(attrs={"class": "input w-full", "autocomplete": "off"}),
        error_messages={"required": "دلیل تغییر را بنویسید"},
    )
    confirm = forms.BooleanField(label="از درستی کد ملی مطمئنم", error_messages={"required": "تایید را علامت بزنید"})

    def clean_code(self) -> str:
        return validate_national_code(normalize_national_code(self.cleaned_data["code"]))

    def clean_note(self) -> str:
        return " ".join(self.cleaned_data["note"].split())
```

---

## گام ۵: viewها

### `apps/panel/views/customers.py` (جدید)

```python
"""Customers in the panel (docs/09 module 11). The national-code lock (D20) opens only here: permission, reason, audit."""

from __future__ import annotations

from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts import services
from apps.accounts.models import User
from apps.engagement.models import Like, Review, StockSubscription
from apps.orders.models import PAID_STATES, Order
from apps.panel import audit, htmx, queries
from apps.panel.forms_settings import NationalCodeForm, first_error
from apps.panel.permissions import panel_view

PAGE_SIZE = 25
VIEW, CHANGE, NATIONAL = "accounts.view_user", "accounts.change_user", "accounts.change_national_code"


def _list_context(params) -> dict:
    queryset = User.objects.filter(is_staff=False).annotate(
        order_count=Count("orders", filter=~Q(orders__status=Order.PENDING)),
        spent=Sum("orders__payable", filter=Q(orders__status__in=PAID_STATES)),
    )
    condition = queries.customer_search_q(params.get("q", ""))
    if condition is not None:
        queryset = queryset.filter(condition)
    state = "inactive" if params.get("state") == "inactive" else ""
    if state:
        queryset = queryset.filter(is_active=False)
    page_obj = Paginator(queryset.order_by("-date_joined", "-pk"), PAGE_SIZE).get_page(params.get("page"))
    filters = {key: value for key, value in (("q", params.get("q", "")), ("state", state)) if value}
    return {"page_obj": page_obj, "q": params.get("q", ""), "state": state, "qs": urlencode(filters)}


@panel_view(VIEW)
@require_GET
def customer_list(request):
    context = _list_context(request.GET)
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "panel/customers/_list_results.html", context)
    return render(request, "panel/customers/list.html", context)


def _customer(pk) -> User:
    return get_object_or_404(User, pk=pk, is_staff=False)


@panel_view(VIEW)
@require_GET
def customer_detail(request, pk):
    customer = _customer(pk)
    user = request.user
    paid = Order.objects.filter(user=customer, status__in=PAID_STATES).aggregate(n=Count("pk"), total=Sum("payable"))
    context = {
        "customer": customer,
        "paid_count": paid["n"],
        "spent": paid["total"] or 0,
        "order_count": Order.objects.filter(user=customer).exclude(status=Order.PENDING).count(),
        "orders": list(Order.objects.filter(user=customer).order_by("-created_at", "-pk")[:10]),
        "addresses": list(customer.addresses.filter(deleted_at__isnull=True).select_related("province", "city")),
        "reviews": list(Review.objects.filter(user=customer).select_related("product").order_by("-created_at")[:10]),
        "like_count": Like.objects.filter(user=customer).count(),
        "likes": list(Like.objects.filter(user=customer).select_related("product").order_by("-created_at")[:10]),
        "subscriptions": list(
            StockSubscription.objects.filter(user=customer, notified_at__isnull=True)
            .select_related("variant__product")
            .order_by("-created_at")[:10]
        ),
        "can_change": user.has_perm(CHANGE),
        "can_national": user.has_perm(NATIONAL),
        "can_orders": user.has_perm("orders.view_order"),
        "nc_form": NationalCodeForm(),
    }
    return render(request, "panel/customers/detail.html", context)


@panel_view(VIEW, CHANGE)
@require_POST
def customer_active(request, pk):
    customer = _customer(pk)
    active = request.POST.get("to") == "1"
    services.set_customer_active(customer, active)
    audit.log(request.user, customer, audit.CHANGE, "فعال‌سازی حساب" if active else "غیرفعال‌سازی حساب")
    htmx.flash(request, "حساب فعال شد" if active else "حساب غیرفعال شد؛ مشتری دیگر نمی‌تواند وارد شود")
    return redirect("panel:customer_detail", pk=pk)


@panel_view(VIEW, CHANGE)
@require_POST
def customer_logout(request, pk):
    customer = _customer(pk)
    services.revoke_sessions(customer)
    audit.log(request.user, customer, audit.CHANGE, "خروج از همه‌ی دستگاه‌ها")
    htmx.flash(request, "مشتری از همه‌ی دستگاه‌ها خارج شد")
    return redirect("panel:customer_detail", pk=pk)


@panel_view(VIEW, NATIONAL)
@require_POST
def customer_national_code(request, pk):
    customer = _customer(pk)
    form = NationalCodeForm(request.POST)
    if not form.is_valid():
        htmx.flash(request, first_error(form), "error")
        return redirect("panel:customer_detail", pk=pk)
    data = form.cleaned_data
    try:
        previous = services.change_national_code(customer, data["code"])
    except services.CustomerError as exc:
        htmx.flash(request, str(exc), "error")
        return redirect("panel:customer_detail", pk=pk)
    audit.log(
        request.user, customer, audit.CHANGE, f"تغییر کد ملی از {previous or 'خالی'} به {data['code']}: {data['note']}"
    )
    htmx.flash(request, "کد ملی تغییر کرد")
    return redirect("panel:customer_detail", pk=pk)
```

### `apps/panel/views/settings.py` (جدید)

```python
"""Settings in the panel (docs/09 module 12): identity, invoice details, sales, advanced (superuser), shipping, gateways."""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.models import SiteSettings
from apps.orders.models import ShippingMethod
from apps.panel.forms_settings import (
    AdvancedForm,
    GatewayForm,
    IdentityForm,
    LegalForm,
    SalesForm,
    ShippingMethodForm,
)
from apps.panel.permissions import panel_view
from apps.panel.views import common
from apps.payments.models import PaymentGateway

SITE, GATEWAY, SHIPPING = "core.change_sitesettings", "payments.change_paymentgateway", "orders.change_shippingmethod"
FORM = "panel/settings/form.html"
TITLES = {"identity": "هویت و تماس", "legal": "مشخصات فاکتور", "sales": "فروش", "advanced": "پیشرفته"}


@panel_view(any_of=(SITE, GATEWAY, SHIPPING))
@require_GET
def settings_index(request):
    for perm, name in (
        (SITE, "panel:settings_identity"),
        (SHIPPING, "panel:shipping_list"),
        (GATEWAY, "panel:gateway_list"),
    ):
        if request.user.has_perm(perm):
            return redirect(name)
    raise Http404


def _logos(site, form, request) -> None:
    for name in ("logo_light", "logo_dark"):
        if form.cleaned_data.get(f"{name}_clear") and not request.FILES.get(name):
            setattr(site, name, "")


def _site_tab(request, form_class, tab, prepare=None):
    site = SiteSettings.objects.get_or_create(pk=1)[0]  # not get_solo(): that one may be a cached copy
    return common.form_view(
        request, form_class, site, template=FORM, heading=TITLES[tab], back="panel:settings_index", noun="تنظیمات",
        prepare=prepare, after=lambda _obj: reverse(f"panel:settings_{tab}"), extra={"tab": tab},
    )  # fmt: skip


@panel_view(SITE)
@require_http_methods(["GET", "POST"])
def settings_identity(request):
    return _site_tab(request, IdentityForm, "identity", _logos)


@panel_view(SITE)
@require_http_methods(["GET", "POST"])
def settings_legal(request):
    return _site_tab(request, LegalForm, "legal")


@panel_view(SITE)
@require_http_methods(["GET", "POST"])
def settings_sales(request):
    return _site_tab(request, SalesForm, "sales")


@panel_view(superuser=True)
@require_http_methods(["GET", "POST"])
def settings_advanced(request):
    return _site_tab(request, AdvancedForm, "advanced")


# --- shipping methods --------------------------------------------------------


@panel_view(SHIPPING)
@require_GET
def shipping_list(request):
    return render(request, "panel/settings/shipping.html", {"methods": ShippingMethod.objects.all(), "tab": "shipping"})


@panel_view(SHIPPING)
@require_http_methods(["GET", "POST"])
def shipping_edit(request, pk):
    method = get_object_or_404(ShippingMethod, pk=pk)
    return common.form_view(
        request, ShippingMethodForm, method, template=FORM, heading="ویرایش روش ارسال", back="panel:shipping_list",
        noun="روش ارسال", extra={"tab": "shipping", "sub": True},
    )  # fmt: skip


# --- gateways ----------------------------------------------------------------


def _gateway_logo(gateway, form, request) -> None:
    if form.cleaned_data.get("logo_clear") and not request.FILES.get("logo"):
        gateway.logo = ""


@panel_view(GATEWAY)
@require_GET
def gateway_list(request):
    return render(
        request, "panel/settings/gateways.html", {"gateways": PaymentGateway.objects.all(), "tab": "gateways"}
    )


@panel_view(GATEWAY)
@require_http_methods(["GET", "POST"])
def gateway_edit(request, pk):
    gateway = get_object_or_404(PaymentGateway, pk=pk)
    return common.form_view(
        request, GatewayForm, gateway, template=FORM, heading="ویرایش درگاه", back="panel:gateway_list",
        noun="درگاه", prepare=_gateway_logo, extra={"tab": "gateways", "sub": True},
    )  # fmt: skip
```

### `apps/panel/views/system.py` (جدید)

```python
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
```

---

## گام ۶: `urls.py` و `nav.py`

**`apps/panel/urls.py`**: `customers`، `settings` و `system` را به importهای `from .views import (...)` اضافه کن. (اسم ماژول `settings` با `django.conf.settings` تداخل ندارد، چون در این فایل از آن استفاده نمی‌شود.) به انتهای `urlpatterns` اضافه کن:

```python
# customers
(path("customers/", customers.customer_list, name="customers"),)
(path("customers/<int:pk>/", customers.customer_detail, name="customer_detail"),)
(path("customers/<int:pk>/active/", customers.customer_active, name="customer_active"),)
(path("customers/<int:pk>/logout/", customers.customer_logout, name="customer_logout"),)
(path("customers/<int:pk>/national-code/", customers.customer_national_code, name="customer_national_code"),)
# settings
(path("settings/", settings.settings_index, name="settings_index"),)
(path("settings/identity/", settings.settings_identity, name="settings_identity"),)
(path("settings/legal/", settings.settings_legal, name="settings_legal"),)
(path("settings/sales/", settings.settings_sales, name="settings_sales"),)
(path("settings/advanced/", settings.settings_advanced, name="settings_advanced"),)
(path("settings/shipping/", settings.shipping_list, name="shipping_list"),)
(path("settings/shipping/<int:pk>/", settings.shipping_edit, name="shipping_edit"),)
(path("settings/gateways/", settings.gateway_list, name="gateway_list"),)
(path("settings/gateways/<int:pk>/", settings.gateway_edit, name="gateway_edit"),)
# system
(path("sms/", system.sms_list, name="sms"),)
(path("system/", system.system_index, name="system"),)
(path("system/staff/", system.staff_list, name="staff"),)
(path("system/staff/new/", system.staff_new, name="staff_new"),)
(path("system/staff/<int:pk>/", system.staff_edit, name="staff_edit"),)
(path("system/staff/<int:pk>/password/", system.staff_password, name="staff_password"),)
(path("system/staff/<int:pk>/active/", system.staff_active, name="staff_active"),)
(path("system/audit/", system.audit_list, name="audit"),)
(path("system/launch/", system.launch, name="launch"),)
```

**`apps/panel/nav.py`**: به انتهای `ITEMS` اضافه کن:

```python
(NavItem("customers", "مشتریان", "panel:customers", icon="users", group="customers", perms=("accounts.view_user",)),)
(
    NavItem(
        "settings",
        "تنظیمات",
        "panel:settings_index",
        icon="settings",
        group="admin",
        perms=("core.change_sitesettings", "payments.change_paymentgateway", "orders.change_shippingmethod"),
    ),
)
(
    NavItem(
        "sms", "گزارش پیامک", "panel:sms", icon="message-circle", group="admin", perms=("notifications.view_smslog",)
    ),
)
(NavItem("system", "سیستم", "panel:system", icon="shield-check", group="admin", superuser=True),)
```

---

## گام ۷: قالب‌ها

قواعد: فقط کلاس‌های منطقی RTL، بدون `font-bold`/`dark:`/رنگ خام Tailwind، ارقام نمایشی با `|fa_digits`/`|fa_text`، یک `btn-primary` در هر صفحه (دکمه‌ی داخل مودال popover استثناست). فقط آیکون‌هایی که قبلاً در قالب‌ها استفاده شده‌اند (`alert-circle`، `info`، `arrow-left`، `lock`).

### `templates/panel/customers/list.html`

```html
{% extends "panel/shell.html" %}
{% block title %}مشتریان{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="مشتریان" %}
    <span id="customers-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  <form action="{% url 'panel:customers' %}" method="get" role="search"
        hx-get="{% url 'panel:customers' %}" hx-target="#customers-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-sync="this:replace" hx-indicator="#customers-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3">
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ q }}" placeholder="موبایل، نام یا کد ملی" class="grow text-small" autocomplete="off">
    </label>
    <select name="state" class="select h-10 w-40 text-small">
      <option value="">همه‌ی حساب‌ها</option>
      <option value="inactive"{% if state == "inactive" %} selected{% endif %}>غیرفعال</option>
    </select>
  </form>
  <div id="customers-results" aria-live="polite">{% include "panel/customers/_list_results.html" %}</div>
</div>
{% endblock %}
```

### `templates/panel/customers/_list_results.html`

```html
{% load core_tags jalali_tags %}
{% if page_obj.object_list %}
  <div class="hidden lg:block bg-base-100 border rounded-box overflow-x-auto">
    <table class="table table-sm">
      <thead><tr>
        <th scope="col">مشتری</th><th scope="col">موبایل</th><th scope="col">سفارش‌ها</th>
        <th scope="col">جمع خرید (تومان)</th><th scope="col">عضویت</th><th scope="col">وضعیت</th>
      </tr></thead>
      <tbody>
        {% for c in page_obj.object_list %}
          <tr class="hover:bg-base-300{% if not c.is_active %} opacity-60{% endif %}">
            <td><a href="{% url 'panel:customer_detail' c.pk %}" class="text-small link link-hover"><bdi>{{ c.get_full_name|default:"بدون نام"|fa_text }}</bdi></a></td>
            <td><span class="num">{{ c.mobile|fa_digits }}</span></td>
            <td><span class="num">{{ c.order_count|fa_digits }}</span></td>
            <td class="whitespace-nowrap">{{ c.spent|default:0|toman }}</td>
            <td class="text-ink-2 whitespace-nowrap"><span class="num">{{ c.date_joined|to_jalali:"%Y/%m/%d" }}</span></td>
            <td><span class="flex items-center gap-2 text-small whitespace-nowrap"><span class="status {% if c.is_active %}status-success{% else %}status-neutral{% endif %}"></span>{% if c.is_active %}فعال{% else %}غیرفعال{% endif %}</span></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <ul class="lg:hidden flex flex-col gap-3">
    {% for c in page_obj.object_list %}
      <li><a href="{% url 'panel:customer_detail' c.pk %}" class="block bg-base-100 border rounded-box p-4 flex flex-col gap-2{% if not c.is_active %} opacity-60{% endif %}">
        <span class="flex items-center justify-between gap-2">
          <span class="text-small font-medium"><bdi>{{ c.get_full_name|default:"بدون نام"|fa_text }}</bdi></span>
          <span class="flex items-center gap-2 text-small"><span class="status {% if c.is_active %}status-success{% else %}status-neutral{% endif %}"></span>{% if c.is_active %}فعال{% else %}غیرفعال{% endif %}</span>
        </span>
        <span class="flex items-center justify-between gap-2 text-label text-ink-3">
          <span class="num">{{ c.mobile|fa_digits }}</span>
          <span><span class="num">{{ c.order_count|fa_digits }}</span> سفارش — <span class="whitespace-nowrap">{{ c.spent|default:0|toman }} تومان</span></span>
        </span>
      </a></li>
    {% endfor %}
  </ul>
  {% include "panel/partials/_pagination.html" with target="#customers-results" %}
{% else %}
  {% include "partials/_empty_state.html" with title="مشتری پیدا نشد" description="عبارت جستجو را تغییر دهید" %}
{% endif %}
```

### `templates/panel/customers/detail.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags jalali_tags panel_tags %}
{% block title %}{{ customer.get_full_name|default:customer.mobile|fa_text }}{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  {% url 'panel:customers' as back_url %}
  {% include "panel/partials/_form_head.html" with back_url=back_url title=customer.get_full_name|default:"مشتری بدون نام"|fa_text %}

  <div class="lg:grid lg:grid-cols-[1fr_320px] lg:gap-6 items-start flex flex-col gap-4">
    <div class="flex flex-col gap-4 min-w-0 w-full">
      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
        <h2 class="text-lead font-medium">پروفایل</h2>
        <dl class="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-small">
          <div class="flex justify-between gap-3"><dt class="text-ink-2">موبایل</dt><dd class="num">{{ customer.mobile|fa_digits }}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-ink-2">کد ملی</dt>
            <dd class="flex items-center gap-1">{% if customer.national_code %}{% icon "lock" size=16 class="text-ink-3" %}<span class="num">{{ customer.national_code|fa_digits }}</span>{% else %}—{% endif %}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-ink-2">ایمیل</dt><dd>{% if customer.email %}<span class="latin">{{ customer.email }}</span>{% else %}—{% endif %}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-ink-2">عضویت</dt><dd class="num">{{ customer.date_joined|to_jalali }}</dd></div>
          <div class="flex justify-between gap-3"><dt class="text-ink-2">آخرین ورود</dt><dd class="num">{% if customer.last_login %}{{ customer.last_login|to_jalali }}{% else %}—{% endif %}</dd></div>
        </dl>
      </section>

      <section class="grid grid-cols-3 gap-3">
        <div class="bg-base-100 border rounded-box p-3 flex flex-col gap-1"><span class="text-label text-ink-3">سفارش‌ها</span><span class="text-lead font-medium num">{{ order_count|fa_digits }}</span></div>
        <div class="bg-base-100 border rounded-box p-3 flex flex-col gap-1"><span class="text-label text-ink-3">پرداخت‌شده</span><span class="text-lead font-medium num">{{ paid_count|fa_digits }}</span></div>
        <div class="bg-base-100 border rounded-box p-3 flex flex-col gap-1"><span class="text-label text-ink-3">جمع خرید</span><span class="text-small font-medium whitespace-nowrap">{{ spent|toman }} تومان</span></div>
      </section>

      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-lead font-medium">آخرین سفارش‌ها</h2>
          {% if can_orders %}<a href="{% url 'panel:orders' %}?tab=all&q={{ customer.mobile }}" class="text-small text-brand-ink">همه‌ی سفارش‌ها</a>{% endif %}
        </div>
        {% for order in orders %}
          <div class="flex items-center justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
            <span class="min-w-0 flex flex-col">
              {% if can_orders %}<a href="{% url 'panel:order_detail' order.number %}" class="latin text-small link link-hover">{{ order.number }}</a>{% else %}<span class="latin text-small">{{ order.number }}</span>{% endif %}
              <span class="text-label text-ink-3 num">{{ order.created_at|to_jalali }}</span>
            </span>
            <span class="flex items-center gap-3 text-small shrink-0"><span class="flex items-center gap-2"><span class="status {{ order.status_dot }}"></span>{{ order.get_status_display }}</span><span class="whitespace-nowrap">{{ order.payable|toman }}</span></span>
          </div>
        {% empty %}<p class="text-small text-ink-2">سفارشی ثبت نشده است</p>{% endfor %}
      </section>

      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
        <h2 class="text-lead font-medium">آدرس‌ها</h2>
        {% for a in addresses %}
          <div class="flex flex-col gap-1 {% if not forloop.first %}border-t pt-3{% endif %}">
            <span class="text-small">{{ a.title|default:a.city.name|fa_text }}{% if a.is_default %} <span class="badge badge-sm badge-soft ms-1">پیش‌فرض</span>{% endif %} — <bdi>{{ a.recipient_name|fa_text }}</bdi> <span class="num">{{ a.recipient_mobile|fa_digits }}</span></span>
            <span class="text-label text-ink-3 leading-5">{{ a.province.name }}، {{ a.city.name }}، {{ a.address_text|fa_text }}، پلاک {{ a.plate|fa_digits }} — <span class="num">{{ a.postal_code|fa_digits }}</span></span>
          </div>
        {% empty %}<p class="text-small text-ink-2">آدرسی ثبت نشده است</p>{% endfor %}
      </section>

      <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-3">
        <h2 class="text-lead font-medium">نظرها</h2>
        {% for review in reviews %}
          <div class="flex items-start justify-between gap-3 {% if not forloop.first %}border-t pt-3{% endif %}">
            <span class="min-w-0 flex flex-col gap-1"><span class="text-small line-clamp-1">{{ review.product.title|fa_text }}</span><span class="text-label text-ink-3 line-clamp-2">{{ review.body|fa_text }}</span></span>
            <span class="flex items-center gap-2 text-small shrink-0 whitespace-nowrap"><span class="status {{ review.status|review_dot }}"></span>{{ review.get_status_display }}</span>
          </div>
        {% empty %}<p class="text-small text-ink-2">نظری ثبت نشده است</p>{% endfor %}
      </section>

      <section class="grid sm:grid-cols-2 gap-4">
        <div class="bg-base-100 border rounded-box p-4 flex flex-col gap-2">
          <h2 class="text-lead font-medium">علاقه‌مندی‌ها <span class="text-small text-ink-3 num">({{ like_count|fa_digits }})</span></h2>
          {% for like in likes %}<span class="text-small line-clamp-1">{{ like.product.title|fa_text }}</span>{% empty %}<p class="text-small text-ink-2">خالی است</p>{% endfor %}
        </div>
        <div class="bg-base-100 border rounded-box p-4 flex flex-col gap-2">
          <h2 class="text-lead font-medium">منتظر «موجود شد»</h2>
          {% for sub in subscriptions %}<span class="text-small line-clamp-1">{{ sub.variant.product.title|fa_text }} — {{ sub.variant.title|fa_text }}</span>{% empty %}<p class="text-small text-ink-2">اشتراک بازی ندارد</p>{% endfor %}
        </div>
      </section>
    </div>

    <aside class="bg-base-100 border rounded-box p-4 flex flex-col gap-3 w-full lg:sticky lg:top-20">
      <h2 class="text-lead font-medium">وضعیت حساب</h2>
      <p class="flex items-center gap-2 text-small"><span class="status {% if customer.is_active %}status-success{% else %}status-neutral{% endif %}"></span>{% if customer.is_active %}فعال{% else %}غیرفعال{% endif %}</p>
      {% if can_change %}
        <form method="post" action="{% url 'panel:customer_active' customer.pk %}"
              data-confirm="{% if customer.is_active %}این حساب غیرفعال شود؟ مشتری دیگر نمی‌تواند وارد شود{% else %}این حساب دوباره فعال شود؟{% endif %}"
              data-confirm-title="{% if customer.is_active %}غیرفعال‌سازی حساب{% else %}فعال‌سازی حساب{% endif %}"
              data-confirm-label="{% if customer.is_active %}غیرفعال کن{% else %}فعال کن{% endif %}"{% if customer.is_active %} data-confirm-tone="danger"{% endif %}>
          {% csrf_token %}<input type="hidden" name="to" value="{% if customer.is_active %}0{% else %}1{% endif %}">
          <button type="submit" class="btn w-full h-10 bg-base-300 border">{% if customer.is_active %}غیرفعال‌سازی حساب{% else %}فعال‌سازی حساب{% endif %}</button>
        </form>
        <form method="post" action="{% url 'panel:customer_logout' customer.pk %}" data-confirm="مشتری از همه‌ی دستگاه‌ها خارج شود؟" data-confirm-title="خروج از همه‌ی دستگاه‌ها" data-confirm-label="خارج کن">
          {% csrf_token %}<button type="submit" class="btn btn-ghost w-full h-10 text-ink-2">خروج از همه‌ی دستگاه‌ها</button>
        </form>
      {% endif %}
      {% if can_national %}
        <button type="button" popovertarget="nc-modal" class="btn btn-ghost w-full h-10 text-ink-2">{% if customer.national_code %}تغییر کد ملی{% else %}ثبت کد ملی{% endif %}</button>
      {% endif %}
    </aside>
  </div>
</div>

{% if can_national %}
  <div class="modal" popover id="nc-modal">
    <div class="modal-box max-w-sm">
      <h3 class="text-lead font-medium">{% if customer.national_code %}تغییر کد ملی{% else %}ثبت کد ملی{% endif %}</h3>
      <p class="text-small text-ink-2 mt-2 leading-6">کد ملی بعد از ثبت برای خود مشتری قفل است و فقط شما با دلیل ثبت‌شده می‌توانید آن را عوض کنید</p>
      <form method="post" action="{% url 'panel:customer_national_code' customer.pk %}" class="mt-4 flex flex-col gap-3" novalidate>
        {% csrf_token %}
        {% include "panel/partials/_field.html" with field=nc_form.code %}
        {% include "panel/partials/_field.html" with field=nc_form.note %}
        <label class="flex items-start gap-2 cursor-pointer"><input type="checkbox" name="confirm" value="1" required class="checkbox checkbox-sm mt-0.5"><span class="text-small">{{ nc_form.confirm.label }}</span></label>
        <div class="flex items-center gap-2 border-t pt-3">
          <button type="submit" class="btn btn-primary flex-1 h-11 min-h-11">ثبت</button>
          <button type="button" popovertarget="nc-modal" popovertargetaction="hide" class="btn btn-ghost h-11 text-ink-2">انصراف</button>
        </div>
      </form>
    </div>
  </div>
{% endif %}
{% endblock %}
```

### `templates/panel/settings/_tabs.html`

```html
<div role="tablist" class="tabs tabs-border overflow-x-auto no-scrollbar">
  {% if perms.core.change_sitesettings %}
    <a role="tab" href="{% url 'panel:settings_identity' %}" class="tab whitespace-nowrap{% if tab == 'identity' %} tab-active{% endif %}">هویت و تماس</a>
    <a role="tab" href="{% url 'panel:settings_legal' %}" class="tab whitespace-nowrap{% if tab == 'legal' %} tab-active{% endif %}">مشخصات فاکتور</a>
    <a role="tab" href="{% url 'panel:settings_sales' %}" class="tab whitespace-nowrap{% if tab == 'sales' %} tab-active{% endif %}">فروش</a>
  {% endif %}
  {% if perms.orders.change_shippingmethod %}<a role="tab" href="{% url 'panel:shipping_list' %}" class="tab whitespace-nowrap{% if tab == 'shipping' %} tab-active{% endif %}">ارسال</a>{% endif %}
  {% if perms.payments.change_paymentgateway %}<a role="tab" href="{% url 'panel:gateway_list' %}" class="tab whitespace-nowrap{% if tab == 'gateways' %} tab-active{% endif %}">درگاه‌ها</a>{% endif %}
  {% if request.user.is_superuser %}<a role="tab" href="{% url 'panel:settings_advanced' %}" class="tab whitespace-nowrap{% if tab == 'advanced' %} tab-active{% endif %}">پیشرفته</a>{% endif %}
</div>
```

### `templates/panel/settings/form.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}{{ heading }}{% endblock %}
{% block content %}
<div class="flex flex-col gap-4 max-w-3xl">
  {% if sub %}
    {% include "panel/partials/_form_head.html" with back_url=back_url title=heading %}
  {% else %}
    {% include "panel/partials/_page_heading.html" with title="تنظیمات" %}
    {% include "panel/settings/_tabs.html" %}
  {% endif %}
  <form method="post" enctype="multipart/form-data" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for e in form.non_field_errors %}<div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ e }}</span></div>{% endfor %}
    {% for field in form.visible_fields %}
      {% if field.name == "logo_light_clear" and not obj.logo_light %}{% elif field.name == "logo_dark_clear" and not obj.logo_dark %}{% elif field.name == "logo_clear" and not obj.logo %}{% else %}{% include "panel/partials/_field.html" %}{% endif %}
    {% endfor %}
    {% include "panel/partials/_save_bar.html" with back_url=back_url %}
  </form>
</div>
{% endblock %}
```

### `templates/panel/settings/shipping.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}روش‌های ارسال{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  {% include "panel/partials/_page_heading.html" with title="تنظیمات" %}
  {% include "panel/settings/_tabs.html" %}
  {% for m in methods %}
    {% if forloop.first %}<ul class="flex flex-col gap-2">{% endif %}
    <li class="bg-base-100 border rounded-box p-3 flex items-center gap-3{% if not m.is_active %} opacity-60{% endif %}">
      <div class="min-w-0 flex-1 flex flex-col gap-1">
        <a href="{% url 'panel:shipping_edit' m.pk %}" class="text-small font-medium line-clamp-1">{{ m.title|fa_text }}</a>
        <span class="flex flex-wrap items-center gap-2 text-label text-ink-3">
          <span class="flex items-center gap-1"><span class="status {% if m.is_active %}status-success{% else %}status-neutral{% endif %}"></span>{% if m.is_active %}فعال{% else %}غیرفعال{% endif %}</span>
          <span class="latin">{{ m.code }}</span><span>{{ m.get_payment_mode_display }}</span>{% if m.has_tracking %}<span>با کد رهگیری</span>{% endif %}
        </span>
      </div>
    </li>
    {% if forloop.last %}</ul>{% endif %}
  {% empty %}
    {% include "partials/_empty_state.html" with title="روش ارسالی ثبت نشده" description="مهاجرت داده‌ی روش تیپاکس اجرا نشده است" %}
  {% endfor %}
</div>
{% endblock %}
```

### `templates/panel/settings/gateways.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}درگاه‌های پرداخت{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  {% include "panel/partials/_page_heading.html" with title="تنظیمات" %}
  {% include "panel/settings/_tabs.html" %}
  {% for g in gateways %}
    {% if forloop.first %}<ul class="flex flex-col gap-2">{% endif %}
    <li class="bg-base-100 border rounded-box p-3 flex items-center gap-3{% if not g.is_active %} opacity-60{% endif %}">
      <span class="w-10 h-10 shrink-0 rounded-lg bg-white border overflow-hidden flex items-center justify-center">
        {% if g.logo %}<img src="{{ g.logo.url }}" alt="" width="40" height="40" loading="lazy" class="w-full h-full object-contain p-1">{% else %}{% icon "info" size=18 class="text-ink-3" %}{% endif %}
      </span>
      <div class="min-w-0 flex-1 flex flex-col gap-1">
        <a href="{% url 'panel:gateway_edit' g.pk %}" class="text-small font-medium line-clamp-1">{{ g.title|fa_text }}</a>
        <span class="flex flex-wrap items-center gap-2 text-label text-ink-3">
          <span class="flex items-center gap-1"><span class="status {% if g.is_active %}status-success{% else %}status-neutral{% endif %}"></span>{% if g.is_active %}فعال{% else %}غیرفعال{% endif %}</span>
          <span class="latin">{{ g.code }}</span>
          <span class="num whitespace-nowrap">{{ g.min_amount|toman }}{% if g.max_amount %} تا {{ g.max_amount|toman }}{% else %} به بالا{% endif %} تومان</span>
        </span>
      </div>
    </li>
    {% if forloop.last %}</ul>{% endif %}
  {% empty %}
    {% include "partials/_empty_state.html" with title="درگاهی ثبت نشده" description="مهاجرت داده‌ی درگاه‌ها اجرا نشده است" %}
  {% endfor %}
</div>
{% endblock %}
```

### `templates/panel/system/_tabs.html`

```html
<div role="tablist" class="tabs tabs-border overflow-x-auto no-scrollbar">
  <a role="tab" href="{% url 'panel:staff' %}" class="tab whitespace-nowrap{% if tab == 'staff' %} tab-active{% endif %}">همکاران</a>
  <a role="tab" href="{% url 'panel:audit' %}" class="tab whitespace-nowrap{% if tab == 'audit' %} tab-active{% endif %}">ممیزی</a>
  <a role="tab" href="{% url 'panel:launch' %}" class="tab whitespace-nowrap{% if tab == 'launch' %} tab-active{% endif %}">آمادگی انتشار</a>
</div>
```

### `templates/panel/system/staff.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags jalali_tags %}
{% block title %}همکاران{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="سیستم" %}
    <a href="{% url 'panel:staff_new' %}" class="btn btn-primary h-10">افزودن همکار</a>
  </div>
  {% include "panel/system/_tabs.html" with tab="staff" %}
  {% if not groups_exist %}<div role="alert" class="alert text-small">{% icon "info" size=18 class="text-ink-2 shrink-0" %}<span>هنوز گروهی ساخته نشده؛ روی سرور setup_groups را اجرا کنید</span></div>{% endif %}
  <ul class="flex flex-col gap-2">
    {% for member in staff %}
      <li class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3{% if not member.is_active %} opacity-60{% endif %}">
        <div class="min-w-0 flex-1 flex flex-col gap-1">
          {% if member.is_superuser %}<span class="text-small font-medium"><bdi>{{ member.get_full_name|default:member.mobile|fa_text }}</bdi></span>
          {% else %}<a href="{% url 'panel:staff_edit' member.pk %}" class="text-small font-medium"><bdi>{{ member.get_full_name|default:member.mobile|fa_text }}</bdi></a>{% endif %}
          <span class="flex flex-wrap items-center gap-2 text-label text-ink-3">
            <span class="num">{{ member.mobile|fa_digits }}</span>
            {% if member.is_superuser %}<span class="badge badge-sm badge-soft">مدیر کل</span>{% endif %}
            {% for group in member.groups.all %}<span class="badge badge-sm badge-soft">{{ group.name }}</span>{% endfor %}
            <span>آخرین ورود: {% if member.last_login %}<span class="num">{{ member.last_login|to_jalali }}</span>{% else %}—{% endif %}</span>
          </span>
        </div>
        <span class="flex items-center gap-2 text-small shrink-0"><span class="status {% if member.is_active %}status-success{% else %}status-neutral{% endif %}"></span>{% if member.is_active %}فعال{% else %}غیرفعال{% endif %}</span>
        {% if member.pk != request.user.pk %}
          <form method="post" action="{% url 'panel:staff_active' member.pk %}" class="shrink-0"
                data-confirm="{% if member.is_active %}این همکار غیرفعال شود؟ دیگر نمی‌تواند وارد پنل شود{% else %}این همکار دوباره فعال شود؟{% endif %}"
                data-confirm-title="{% if member.is_active %}غیرفعال‌سازی همکار{% else %}فعال‌سازی همکار{% endif %}"
                data-confirm-label="{% if member.is_active %}غیرفعال کن{% else %}فعال کن{% endif %}"{% if member.is_active %} data-confirm-tone="danger"{% endif %}>
            {% csrf_token %}<input type="hidden" name="to" value="{% if member.is_active %}0{% else %}1{% endif %}">
            <button type="submit" class="btn btn-ghost btn-sm h-10 text-ink-2 whitespace-nowrap">{% if member.is_active %}غیرفعال کن{% else %}فعال کن{% endif %}</button>
          </form>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
</div>
{% endblock %}
```

### `templates/panel/system/staff_form.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags %}
{% block title %}{{ heading }}{% endblock %}
{% block content %}
<div class="flex flex-col gap-4 max-w-xl">
  {% url 'panel:staff' as back_url %}
  {% include "panel/partials/_form_head.html" with back_url=back_url title=heading %}
  <form method="post" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate>
    {% csrf_token %}
    {% for e in form.non_field_errors %}<div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>{{ e }}</span></div>{% endfor %}
    {% if member %}<p class="text-small text-ink-2">موبایل: <span class="num">{{ member.mobile|fa_digits }}</span></p>{% endif %}
    {% for field in form.visible_fields %}{% include "panel/partials/_field.html" %}{% endfor %}
    {% include "panel/partials/_save_bar.html" with back_url=back_url label=label %}
  </form>
  {% if member %}
    <form method="post" action="{% url 'panel:staff_password' member.pk %}" class="bg-base-100 border rounded-box p-4 flex flex-col gap-4" novalidate
          data-confirm="رمز همکار عوض شود و از همه‌ی دستگاه‌ها خارج شود؟" data-confirm-title="ریست رمز" data-confirm-label="ریست کن">
      {% csrf_token %}
      <h2 class="text-lead font-medium">ریست رمز</h2>
      {% for field in password_form.visible_fields %}{% include "panel/partials/_field.html" %}{% endfor %}
      <button type="submit" class="btn w-full h-11 min-h-11 bg-base-300 border">ثبت رمز تازه</button>
    </form>
  {% endif %}
</div>
{% endblock %}
```

### `templates/panel/system/sms.html`

```html
{% extends "panel/shell.html" %}
{% load static %}
{% block title %}گزارش پیامک{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="گزارش پیامک" %}
    <span id="sms-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  <form action="{% url 'panel:sms' %}" method="get" role="search"
        hx-get="{% url 'panel:sms' %}" hx-target="#sms-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="input changed delay:300ms, change, submit" hx-sync="this:replace" hx-indicator="#sms-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3">
    <label class="input h-10 grow min-w-48 flex items-center gap-2">
      <input type="search" name="q" value="{{ q }}" placeholder="شماره‌ی موبایل" class="grow text-small" autocomplete="off">
    </label>
    <select name="kind" class="select h-10 w-44 text-small">
      <option value="">همه‌ی قالب‌ها</option>
      {% for code in kinds %}<option value="{{ code }}"{% if code == kind %} selected{% endif %}>{{ code }}</option>{% endfor %}
    </select>
    <select name="status" class="select h-10 w-40 text-small">
      <option value="">همه‌ی وضعیت‌ها</option>
      {% for code, label in status_choices %}<option value="{{ code }}"{% if code == status %} selected{% endif %}>{{ label }}</option>{% endfor %}
    </select>
    <div class="contents" data-date-range>
      <input type="text" name="from" value="{{ date_from }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="از تاریخ" class="input h-10 w-36 num text-small">
      <input type="text" name="to" value="{{ date_to }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="تا تاریخ" class="input h-10 w-36 num text-small">
      <span class="hidden text-label text-error" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد</span>
    </div>
  </form>
  <div id="sms-results" aria-live="polite">{% include "panel/system/_sms_results.html" %}</div>
</div>
{% endblock %}
{% block extra_js %}<script src="{% static 'js/jalali_picker.js' %}" defer></script>{% endblock %}
```

### `templates/panel/system/_sms_results.html`

```html
{% load core_tags jalali_tags panel_tags %}
{% if page_obj.object_list %}
  <div class="bg-base-100 border rounded-box overflow-x-auto">
    <table class="table table-sm">
      <thead><tr><th scope="col">زمان</th><th scope="col">موبایل</th><th scope="col">قالب</th><th scope="col">وضعیت</th><th scope="col">شناسه / خطا</th></tr></thead>
      <tbody>
        {% for log in page_obj.object_list %}
          <tr class="hover:bg-base-300">
            <td class="text-ink-2 whitespace-nowrap"><span class="num">{{ log.created_at|to_jalali }}</span></td>
            <td><span class="num">{{ log.mobile|fa_digits }}</span></td>
            <td><span class="latin">{{ log.kind }}</span></td>
            <td><span class="flex items-center gap-2 text-small whitespace-nowrap"><span class="status {{ log.status|sms_dot }}"></span>{{ log.get_status_display }}</span></td>
            <td class="text-label text-ink-3">{% if log.error %}<span class="latin">{{ log.error|truncatechars:90 }}</span>{% elif log.provider_message_id %}<span class="latin">{{ log.provider_message_id }}</span>{% endif %}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% include "panel/partials/_pagination.html" with target="#sms-results" %}
{% else %}
  {% include "partials/_empty_state.html" with title="پیامکی پیدا نشد" description="فیلترها را تغییر دهید" %}
{% endif %}
```

### `templates/panel/system/audit.html`

```html
{% extends "panel/shell.html" %}
{% load static %}
{% block title %}ممیزی{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="سیستم" %}
    <span id="audit-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  {% include "panel/system/_tabs.html" with tab="audit" %}
  <form action="{% url 'panel:audit' %}" method="get"
        hx-get="{% url 'panel:audit' %}" hx-target="#audit-results" hx-swap="innerHTML" hx-push-url="true"
        hx-trigger="change, submit" hx-sync="this:replace" hx-indicator="#audit-indicator"
        class="bg-base-100 border rounded-box p-3 flex flex-wrap items-center gap-3">
    <select name="user" class="select h-10 w-44 text-small">
      <option value="">همه‌ی همکاران</option>
      {% for u in users %}<option value="{{ u.pk }}"{% if u.pk == user_id %} selected{% endif %}>{{ u.get_full_name|default:u.mobile }}</option>{% endfor %}
    </select>
    <select name="type" class="select h-10 w-44 text-small">
      <option value="">همه‌ی بخش‌ها</option>
      {% for t in types %}<option value="{{ t.pk }}"{% if t.pk == type_id %} selected{% endif %}>{{ t.name }}</option>{% endfor %}
    </select>
    <div class="contents" data-date-range>
      <input type="text" name="from" value="{{ date_from }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="از تاریخ" class="input h-10 w-36 num text-small">
      <input type="text" name="to" value="{{ date_to }}" data-jalali-date data-clearable dir="ltr" inputmode="none" autocomplete="off" placeholder="تا تاریخ" class="input h-10 w-36 num text-small">
      <span class="hidden text-label text-error" data-date-range-error>تاریخ شروع نباید بعد از پایان باشد</span>
    </div>
  </form>
  <div id="audit-results" aria-live="polite">{% include "panel/system/_audit_results.html" %}</div>
</div>
{% endblock %}
{% block extra_js %}<script src="{% static 'js/jalali_picker.js' %}" defer></script>{% endblock %}
```

### `templates/panel/system/_audit_results.html`

```html
{% load core_tags jalali_tags %}
{% if rows %}
  <div class="bg-base-100 border rounded-box overflow-x-auto">
    <table class="table table-sm">
      <thead><tr><th scope="col">زمان</th><th scope="col">همکار</th><th scope="col">عمل</th><th scope="col">مورد</th><th scope="col">شرح</th></tr></thead>
      <tbody>
        {% for row in rows %}
          <tr class="hover:bg-base-300">
            <td class="text-ink-2 whitespace-nowrap"><span class="num">{{ row.entry.action_time|to_jalali }}</span></td>
            <td class="whitespace-nowrap"><bdi>{{ row.entry.user.get_full_name|default:row.entry.user.mobile|fa_text }}</bdi></td>
            <td class="whitespace-nowrap text-small">{{ row.action }}</td>
            <td class="text-small"><span class="text-ink-3">{{ row.entry.content_type.name }}</span> — {{ row.entry.object_repr|fa_text }}</td>
            <td class="text-small text-ink-2">{{ row.message|fa_text }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% include "panel/partials/_pagination.html" with target="#audit-results" %}
{% else %}
  {% include "partials/_empty_state.html" with title="موردی ثبت نشده" description="فقط تغییرهایی که از پنل انجام شده‌اند در این فهرست‌اند" %}
{% endif %}
```

### `templates/panel/system/launch.html`

```html
{% extends "panel/shell.html" %}
{% load core_tags jalali_tags %}
{% block title %}آمادگی انتشار{% endblock %}
{% block content %}
<div class="flex flex-col gap-4">
  <div class="flex items-center justify-between gap-3">
    {% include "panel/partials/_page_heading.html" with title="سیستم" %}
    <span id="launch-indicator" class="htmx-indicator loading loading-spinner loading-sm" aria-hidden="true"></span>
  </div>
  {% include "panel/system/_tabs.html" with tab="launch" %}
  <div class="flex items-center justify-between gap-3">
    <p class="text-small text-ink-2">همان بررسی دستور check_launch؛ مواردی که با .env یا سرور درست می‌شوند لینک رفع ندارند</p>
    <button type="button" class="btn h-10 bg-base-300 border shrink-0" hx-get="{% url 'panel:launch' %}" hx-target="#launch-results" hx-swap="innerHTML"
            hx-indicator="#launch-indicator" hx-disabled-elt="this">بررسی دوباره</button>
  </div>
  <div id="launch-results" aria-live="polite">{% include "panel/system/_launch_results.html" %}</div>

  <section class="bg-base-100 border rounded-box p-4 flex flex-col gap-2">
    <h2 class="text-lead font-medium">پشتیبان دیتابیس</h2>
    {% if backup is None %}
      <p class="text-small text-ink-2">BACKUP_DIR تنظیم نشده یا پوشه‌اش وجود ندارد</p>
    {% elif not backup.name %}
      <p class="text-small text-ink-2">هنوز نسخه‌ی پشتیبانی ساخته نشده</p>
    {% else %}
      <p class="text-small"><span class="latin">{{ backup.name }}</span> — <span class="num">{{ backup.at|to_jalali }}</span></p>
      {% if backup.stale %}<p class="text-small text-ink-2 flex items-center gap-1">{% icon "alert-circle" size=18 class="text-ink-3" %}آخرین نسخه بیش از دو روز پیش است؛ کران backup_db را بررسی کنید</p>{% endif %}
    {% endif %}
  </section>
</div>
{% endblock %}
```

### `templates/panel/system/_launch_results.html`

```html
{% load core_tags %}
{% if failed %}
  <div role="alert" class="alert alert-error text-small">{% icon "alert-circle" size=18 class="shrink-0" %}<span>بررسی انجام نشد؛ لاگ سرور را ببینید</span></div>
{% else %}
  <div class="flex flex-col gap-3">
    <p class="text-small text-ink-2"><span class="num">{{ errors|fa_digits }}</span> خطا، <span class="num">{{ warnings|fa_digits }}</span> هشدار</p>
    {% for item in findings %}
      {% if forloop.first %}<ul class="flex flex-col gap-2">{% endif %}
      <li class="bg-base-100 border rounded-box p-3 flex items-start gap-3">
        <span class="flex items-center gap-2 text-small shrink-0 whitespace-nowrap"><span class="status {% if item.error %}status-error{% else %}status-warning{% endif %}"></span>{% if item.error %}خطا{% else %}هشدار{% endif %}</span>
        <span class="text-small flex-1 min-w-0">{{ item.text|fa_text }}</span>
        {% if item.fix %}<a href="{{ item.fix }}" class="btn btn-ghost btn-sm h-10 text-brand-ink shrink-0">رفع</a>{% endif %}
      </li>
      {% if forloop.last %}</ul>{% endif %}
    {% empty %}
      {% include "partials/_empty_state.html" with title="مورد بازی نیست" description="همه‌ی بررسی‌ها پاس شد" %}
    {% endfor %}
  </div>
{% endif %}
```

---

## گام ۸: تست‌ها (فقط همین پنج مورد، فایل جدید)

`apps/panel/tests/test_p14.py`. اگر در `apps/panel/tests/` helper ورود کارمند هست از همان استفاده کن، وگرنه این helper:

```python
"""P14 business rules: staff protection, the national-code lock, settings guards, check_launch compatibility."""

from __future__ import annotations

import time

import pytest
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.urls import reverse

from apps.accounts import services
from apps.accounts.models import User
from apps.core.management.commands import check_launch

pytestmark = pytest.mark.django_db
STRONG = "Str0ng-pass-92"


def panel_login(client, user):
    client.force_login(user)
    session = client.session
    session["panel_login_at"] = int(time.time())
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
    return client


def test_staff_rules_protect_customers_and_the_last_superuser(buyer):
    with pytest.raises(services.StaffError) as exc:
        services.create_staff_user(buyer.mobile, STRONG, [], allow_existing=False)
    assert exc.value.code == "customer"

    member = services.create_staff_user("09120000007", STRONG, [], allow_existing=False)
    assert member.is_staff and not member.is_superuser

    boss = User.objects.create_superuser("09120000009", STRONG)
    with pytest.raises(services.StaffError) as exc:
        services.set_staff_active(boss, by=boss, active=False)
    assert exc.value.code == "self"
    with pytest.raises(services.StaffError) as exc:
        services.set_staff_active(boss, by=member, active=False)
    assert exc.value.code == "last_superuser"


def test_staff_password_reset_ends_their_sessions():
    member = services.create_staff_user("09120000007", STRONG, [], allow_existing=False)
    before = member.session_version
    services.reset_staff_password(member, "An0ther-pass-77")
    member.refresh_from_db()
    assert member.session_version == before + 1 and member.check_password("An0ther-pass-77")


def test_national_code_change_needs_permission_a_reason_and_leaves_an_audit_entry(client, buyer):
    staff = User.objects.create_user("09120000006", is_staff=True)
    staff.user_permissions.add(Permission.objects.get(content_type__app_label="accounts", codename="view_user"))
    panel_login(client, staff)
    url = reverse("panel:customer_national_code", args=[buyer.pk])
    data = {"code": "0499370899", "note": "اصلاح به درخواست مشتری", "confirm": "1"}

    assert client.post(url, data).status_code == 403  # view_user alone does not open the D20 lock
    buyer.refresh_from_db()
    assert buyer.national_code == "0012345679"

    staff.user_permissions.add(Permission.objects.get(codename="change_national_code"))
    assert client.post(url, {**data, "note": ""}).status_code == 302  # no reason: refused
    buyer.refresh_from_db()
    assert buyer.national_code == "0012345679"

    assert client.post(url, data).status_code == 302
    buyer.refresh_from_db()
    assert buyer.national_code == "0499370899"
    assert LogEntry.objects.filter(object_id=str(buyer.pk), change_message__contains="کد ملی").exists()


def test_last_active_shipping_method_cannot_be_deactivated(client, checkout_env):
    boss = User.objects.create_superuser("09120000005", STRONG)
    panel_login(client, boss)
    response = client.post(
        reverse("panel:shipping_edit", args=[checkout_env.pk]), {"title": checkout_env.title, "sort": "0"}
    )
    checkout_env.refresh_from_db()
    assert response.status_code == 200 and checkout_env.is_active  # form re-rendered with the error


def test_collect_detailed_keeps_the_collect_output():
    assert [(level, text) for level, text, _ in check_launch.collect_detailed()] == list(check_launch.collect())
```

اگر فقط یک روش ارسال فعال در دیتابیس تست نیست و تست چهارم همین به‌خاطر seed شکست خورد، خودت داده را در همان تست مهیا کن (روش‌های دیگر را با `save()` غیرفعال کن، نه `update()`).

---

## گام ۹: پایان کار

1. فقط همین‌ها را اجرا کن (با همان متغیرهای محیطی گام ۰):
   ```powershell
   uv run python scripts/build_sprite.py
   uv run ruff check .
   uv run ruff format .
   pnpm run build:css
   uv run pytest -q
   ```
   اگر `pnpm` به‌خاطر محیط شکست خورد، سراغ رفعش نرو. در گزارش بنویس که باید خودم اجرا کنم. نتیجه‌ی `pytest` را با خط پایه‌ی گام ۰ مقایسه کن.
2. گریپ‌های `04` بخش ۱۳ روی `templates/panel/` (چهار الگوی همان بخش) را اجرا کن. نتیجه باید صفر باشد.
3. `build_sprite.py` نباید آیکون ناموجود بدهد. اگر `users` یا `settings` در `static/src/sprite.svg` نبود، نام نزدیک موجود را جایگزین کن (مثلاً `user` / `sliders-horizontal`) و بنویس.

### اسناد (فقط این‌ها)

- `docs/09-panel-spec.md`:
  - ماژول‌های ۱۱ تا ۱۴ را با کد هم‌تراز کن.
  - انحراف‌ها را ثبت کن: مسیر `/panel/sms/`، `payment_mode` فقط‌خواندنی، لوگو فقط jpg/png/webp، تب «پیشرفته» (OTP و `trust_marks_html` برای superuser)، ثبت‌نشدن مدیر کل.
  - یک خط «تغییرات» بنویس.
- `docs/phases/STATUS.md`: ردیف P14 را به ✅ ببر و یک یادداشت کوتاه بنویس.
- `docs/deploy.md` بخش ۸: یک خط اضافه کن که همکار تازه از پنل (سیستم ← همکاران) ساخته می‌شود و بعد از این فاز `setup_groups` باید یک‌بار دیگر اجرا شود (مجوز `accounts.view_user` برای گروه «فروش»).

---

## گزارش پایانی (قالب)

در چند خط بنویس: چه ساخته شد، انحراف‌ها، نتیجه‌ی `pytest` نسبت به خط پایه، و سوال باز ۴ (گروه چهارم؟). همچنین بنویس که بج «سفارش/بازگشت وجه» و provider جستجوی سفارش/محصول هنوز در `providers.py` ثبت نیست و باید در P15 اضافه شود.

## کارهای من (کاربر)

- اجرای `uv run python manage.py setup_groups` (مجوز مشتریان برای «فروش»).
- پاسخ به سوال گروه چهارم.

## فهرست بررسی چشمی (برای من، نه برای Claude Code)

دو تم، عرض ۳۲۰ و ۱۲۸۰:

1. **مشتریان:**
   - جستجو (موبایل با ارقام فارسی، نام، کد ملی) و فیلتر «غیرفعال».
   - جدول در دسکتاپ و کارت در موبایل.
   - جزئیات: غیرفعال/فعال‌سازی با دیالوگ تایید، خروج از همه‌ی دستگاه‌ها، مودال کد ملی (دلیل اجباری، پیام خطا بعد از رد) و آیکون قفل کنار کد ملی.
2. **تنظیمات:**
   - تب‌ها با دو نقش مختلف (superuser و «فروش»).
   - پیش‌نمایش لوگو و حذف لوگو.
   - خطای ساعت‌های «موجود شد».
   - فیلد «نحوه‌ی پرداخت کرایه» فقط‌خواندنی.
   - پیام خطای غیرفعال‌کردن آخرین روش ارسال یا درگاه و تیک تایید درگاه.
3. **سیستم** (superuser):
   - همکاران: ساخت، ویرایش گروه‌ها، ریست رمز، غیرفعال‌کردن خودم و مدیر کل (باید رد شود).
   - ممیزی: فیلتر کاربر، بخش و تاریخ شمسی.
   - آمادگی انتشار: لینک‌های «رفع» کار می‌کنند و کارت پشتیبان درست نشان داده می‌شود.
4. **گزارش پیامک** با نقش غیر superuser که `view_smslog` دارد.
5. **ناوبری:** آیتم‌های تازه فقط برای نقش مجاز دیده می‌شوند و هنگام باز بودن «سیستم»، «پیامک» روشن نمی‌شود.
6. **جستجوی سراسری:** نتیجه‌ی «مشتریان» با موبایل و نام.