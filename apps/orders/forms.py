"""Checkout buyer form: only the still-empty profile fields (D07)."""

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
            # inputs live outside the <form> element (nested forms are invalid)
            field.widget.attrs["form"] = FORM_ID

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
