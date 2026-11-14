"""Form widgets that show Persian digits while the server keeps ASCII (D30)."""

from __future__ import annotations

from django import forms

from apps.core.jalali import to_fa_digits
from apps.core.text import to_fa_text


class FaDigitsInput(forms.TextInput):
    """Mobile, postal code, national code: Persian on screen, normalized to ASCII by the form's clean_*."""

    def __init__(self, attrs=None):
        defaults = {"dir": "ltr", "inputmode": "numeric", "autocomplete": "off", "data-fa-digits": "1"}
        super().__init__({**defaults, **(attrs or {})})

    def format_value(self, value):
        formatted = super().format_value(value)
        return to_fa_digits(formatted) if formatted else formatted


class FaTextInput(forms.TextInput):
    def format_value(self, value):
        formatted = super().format_value(value)
        return to_fa_text(formatted) if formatted else formatted


class FaTextarea(forms.Textarea):
    def format_value(self, value):
        formatted = super().format_value(value)
        return to_fa_text(formatted) if formatted else formatted
