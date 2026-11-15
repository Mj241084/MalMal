"""Admin helpers for the Jalali picker (docs/06). Conversion logic stays in jalali_forms.py."""

from __future__ import annotations

from django import forms

from apps.core.jalali_forms import JalaliDateTimeField, normalize_digits_and_separators


class JalaliDateWidget(forms.TextInput):
    """A text input that static/js/jalali_picker.js turns into a read-only calendar field."""

    class Media:
        css = {"all": ("css/jalali_admin.css",)}
        js = ("js/jalali_picker.js",)

    def __init__(self, attrs=None):
        defaults = {
            "data-jalali-date": "",
            "data-clearable": "",
            "dir": "ltr",
            "inputmode": "none",
            "autocomplete": "off",
            "placeholder": "۱۴۰۵/۰۷/۲۰",
            "class": "vTextField",
        }
        super().__init__({**defaults, **(attrs or {})})


class EndOfDayJalaliDateTimeField(JalaliDateTimeField):
    """A bare date means the END of that day (23:59), so «until 1405/07/20» includes the 20th."""

    def to_python(self, value):
        result = super().to_python(value)
        if result is not None and isinstance(value, str) and len(normalize_digits_and_separators(value).split()) == 1:
            result = result.replace(hour=23, minute=59)
        return result
