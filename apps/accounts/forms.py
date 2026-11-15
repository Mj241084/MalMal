"""Account forms: OTP login, profile, addresses."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.urls import reverse_lazy

from apps.accounts.models import Address, User
from apps.core.forms import FieldErrorAttrsMixin
from apps.core.text import normalize_digits, normalize_fa
from apps.core.validators import normalize_iran_mobile, normalize_national_code, validate_national_code
from apps.core.widgets import FaDigitsInput, FaTextarea, FaTextInput
from apps.geo.models import City, Province

IRAN_LAT_MIN = Decimal("24")
IRAN_LAT_MAX = Decimal("40.5")
IRAN_LNG_MIN = Decimal("43")
IRAN_LNG_MAX = Decimal("64")
COORD_QUANT = Decimal("0.000001")


class MobileForm(FieldErrorAttrsMixin, forms.Form):
    mobile = forms.CharField(
        max_length=20,
        label="شماره موبایل",
        widget=FaDigitsInput(
            attrs={"autocomplete": "tel", "class": "input input-lg w-full text-end num", "data-autofocus": "1"}
        ),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_mobile(self) -> str:
        try:
            return normalize_iran_mobile(self.cleaned_data["mobile"])
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

    def clean_next(self) -> str:
        return (self.cleaned_data.get("next") or "").strip()


class OTPCodeForm(FieldErrorAttrsMixin, forms.Form):
    skip_error_class_fields = ("code",)

    mobile = forms.CharField(widget=forms.HiddenInput)
    code = forms.CharField(
        max_length=8,
        label="کد تایید",
        widget=forms.TextInput(
            attrs={
                "data-otp": "",
                "data-otp-length": "4",
                "data-otp-submit": "otp-verify-submit",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "dir": "ltr",
                "class": "input input-lg w-full text-center num",
            }
        ),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].widget.attrs["maxlength"] = "4"

    def clean_mobile(self) -> str:
        try:
            return normalize_iran_mobile(self.cleaned_data["mobile"])
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

    def clean_code(self) -> str:
        raw = normalize_digits(self.cleaned_data.get("code") or "")
        code = "".join(ch for ch in raw if not ch.isspace())
        if len(code) != 4 or not code.isascii() or not code.isdigit():
            raise forms.ValidationError("کد تایید ۴ رقم است")
        return code

    def clean_next(self) -> str:
        return (self.cleaned_data.get("next") or "").strip()


class ProfileForm(FieldErrorAttrsMixin, forms.ModelForm):
    national_code_confirm = forms.BooleanField(
        required=False,
        label="از درستی کد ملی مطمئن هستم و می‌دانم بعد از ثبت قابل تغییر نیست",
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-sm mt-0.5"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "national_code", "email"]
        labels = {
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "national_code": "کد ملی",
            "email": "ایمیل (اختیاری)",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input w-full", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "input w-full", "autocomplete": "family-name"}),
            "national_code": FaDigitsInput(
                attrs={"class": "input w-full text-end num", "maxlength": "10", "data-digits-only": "1"}
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input w-full text-end latin",
                    "dir": "ltr",
                    "autocomplete": "email",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = False
        self.fields["national_code"].required = False
        if self.instance.national_code:
            # D20: locked after the first save; the value posted by the client is ignored.
            self.fields["national_code"].disabled = True
            self.fields["national_code_confirm"].disabled = True

    def clean_national_code(self) -> str:
        if self.instance.national_code:
            return self.instance.national_code
        code = normalize_national_code(self.cleaned_data.get("national_code") or "")
        if not code:
            return ""
        try:
            return validate_national_code(code)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

    def clean_email(self) -> str:
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("national_code") or ""
        if code and not self.instance.national_code and not cleaned.get("national_code_confirm"):
            self.add_error("national_code", "برای ثبت کد ملی، تایید قیدشده را علامت بزنید")
        return cleaned

    def clean_first_name(self) -> str:
        return normalize_fa(self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self) -> str:
        return normalize_fa(self.cleaned_data.get("last_name") or "").strip()


class AddressForm(FieldErrorAttrsMixin, forms.ModelForm):
    recipient_mobile = forms.CharField(
        max_length=20,
        label="موبایل گیرنده",
        widget=FaDigitsInput(attrs={"class": "input w-full text-end num", "autocomplete": "tel"}),
    )
    lat = forms.DecimalField(required=False, max_digits=12, decimal_places=8, widget=forms.HiddenInput)
    lng = forms.DecimalField(required=False, max_digits=12, decimal_places=8, widget=forms.HiddenInput)

    class Meta:
        model = Address
        fields = [
            "title",
            "recipient_name",
            "recipient_mobile",
            "province",
            "city",
            "address_text",
            "plate",
            "unit",
            "postal_code",
            "lat",
            "lng",
            "is_default",
        ]
        labels = {
            "title": "عنوان (اختیاری)",
            "recipient_name": "نام گیرنده",
            "province": "استان",
            "city": "شهر",
            "address_text": "آدرس کامل",
            "plate": "پلاک",
            "unit": "واحد (اختیاری)",
            "postal_code": "کدپستی",
            "is_default": "آدرس پیش‌فرض",
        }
        widgets = {
            "title": FaTextInput(attrs={"class": "input w-full"}),
            "recipient_name": forms.TextInput(attrs={"class": "input w-full", "autocomplete": "name"}),
            "province": forms.Select(attrs={"class": "select w-full"}),
            "city": forms.Select(attrs={"class": "select w-full"}),
            "address_text": FaTextarea(attrs={"class": "textarea w-full", "rows": 3}),
            "plate": FaTextInput(attrs={"class": "input w-full", "data-fa-digits": "1"}),
            "unit": FaTextInput(attrs={"class": "input w-full", "data-fa-digits": "1"}),
            "postal_code": FaDigitsInput(
                attrs={"class": "input w-full text-end num", "maxlength": "10", "data-digits-only": "1"}
            ),
            "is_default": forms.CheckboxInput(attrs={"class": "checkbox checkbox-sm"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["province"].queryset = Province.objects.order_by("sort", "name")
        self.fields["province"].empty_label = "انتخاب استان"
        self.fields["city"].queryset = City.objects.none()
        self.fields["province"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("geo:city_options"),
                "hx-target": "#id_city",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
                "hx-include": "this",
                "hx-indicator": "#city-indicator",
            }
        )

        province_id = None
        if self.is_bound:
            raw_province = str(self.data.get(self.add_prefix("province")) or "").strip()
            if raw_province.isdigit():
                province_id = int(raw_province)
        elif self.instance.pk and self.instance.province_id:
            province_id = self.instance.province_id

        if province_id is not None:
            cities = City.objects.filter(province_id=province_id)
            if self.is_bound:
                posted_city = str(self.data.get(self.add_prefix("city")) or "").strip()
                if posted_city.isdigit():
                    cities = City.objects.filter(Q(province_id=province_id) | Q(pk=int(posted_city)))
            self.fields["city"].queryset = cities.order_by("name")
            self.fields["city"].empty_label = "انتخاب شهر"
        else:
            self.fields["city"].empty_label = "ابتدا استان را انتخاب کنید"

        if user is not None and not self.instance.pk:
            self.fields["recipient_mobile"].initial = user.mobile
            self.fields["recipient_name"].initial = user.get_full_name()

    def _clean_coord(self, key: str) -> Decimal | None:
        raw = self.cleaned_data.get(key)
        if raw is None or raw == "":
            return None
        try:
            return Decimal(raw).quantize(COORD_QUANT, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as exc:
            raise forms.ValidationError("مختصات نقشه معتبر نیست") from exc

    def clean_lat(self) -> Decimal | None:
        return self._clean_coord("lat")

    def clean_lng(self) -> Decimal | None:
        return self._clean_coord("lng")

    def clean_city(self):
        city = self.cleaned_data.get("city")
        province = self.cleaned_data.get("province")
        if city and province and city.province_id != province.pk:
            raise forms.ValidationError("شهر انتخاب‌شده متعلق به این استان نیست")
        return city

    def clean_recipient_mobile(self) -> str:
        try:
            return normalize_iran_mobile(self.cleaned_data.get("recipient_mobile"))
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc

    def clean_postal_code(self) -> str:
        code = normalize_digits(self.cleaned_data.get("postal_code") or "").strip()
        if len(code) != 10 or not code.isascii() or not code.isdigit():
            raise forms.ValidationError("کدپستی باید دقیقاً ۱۰ رقم باشد")
        return code

    def clean_title(self) -> str:
        return normalize_fa(self.cleaned_data.get("title") or "").strip()

    def clean_recipient_name(self) -> str:
        return normalize_fa(self.cleaned_data.get("recipient_name") or "").strip()

    def clean_address_text(self) -> str:
        return normalize_fa(self.cleaned_data.get("address_text") or "").strip()

    def clean_plate(self) -> str:
        return normalize_fa(self.cleaned_data.get("plate") or "").strip()

    def clean_unit(self) -> str:
        return normalize_fa(self.cleaned_data.get("unit") or "").strip()

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get("lat")
        lng = cleaned.get("lng")
        if (lat is None) != (lng is None):
            raise forms.ValidationError("مختصات نقشه ناقص است")
        if (
            lat is not None
            and lng is not None
            and not (IRAN_LAT_MIN <= lat <= IRAN_LAT_MAX and IRAN_LNG_MIN <= lng <= IRAN_LNG_MAX)
        ):
            raise forms.ValidationError("مختصات انتخاب‌شده خارج از محدوده‌ی ایران است")
        return cleaned
