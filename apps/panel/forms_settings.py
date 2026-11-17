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
            last = not any(g.pk != self.instance.pk for g in gateways.available())
            if last and not cleaned.get("confirm_last"):
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
