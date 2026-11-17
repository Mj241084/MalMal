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
