"""Form fields for money and counts: Persian or Arabic digits and thousands separators in, plain integers out."""

from __future__ import annotations

import re

from django import forms

from apps.core.text import normalize_digits
from apps.core.widgets import FaDigitsInput

MAX_TOMAN = 10**10
_SEPARATORS = re.compile(r"[\s,٬،_]")


class FaIntegerField(forms.IntegerField):
    widget = FaDigitsInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.widget.attrs.setdefault("class", "input w-full text-end num")

    def to_python(self, value):
        if isinstance(value, str):
            value = _SEPARATORS.sub("", normalize_digits(value))
        return super().to_python(value)


class TomanField(FaIntegerField):
    """Whole Toman, never a float (D14). The live "۱٬۲۵۰٬۰۰۰ تومان" hint is attached by panel.js."""

    def __init__(self, *, min_value: int = 0, max_value: int = MAX_TOMAN, **kwargs):
        super().__init__(min_value=min_value, max_value=max_value, **kwargs)
        self.widget.attrs.setdefault("data-toman-hint", "1")
        self.widget.attrs.setdefault("class", "input w-full text-end num")
