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
