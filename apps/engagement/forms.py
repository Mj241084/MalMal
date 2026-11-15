"""Review form: rating + text. Digits are stored as ASCII, shown as Persian (D30)."""

from __future__ import annotations

import re

from django import forms

from apps.core.forms import FieldErrorAttrsMixin
from apps.core.text import normalize_fa
from apps.core.widgets import FaTextarea

BODY_MIN = 10
BODY_MAX = 1500
_BLANK_LINES = re.compile(r"\n{3,}")


class ReviewForm(FieldErrorAttrsMixin, forms.Form):
    rating = forms.TypedChoiceField(
        choices=[(str(n), str(n)) for n in range(1, 6)],
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={"required": "امتیاز را انتخاب کنید", "invalid_choice": "امتیاز را انتخاب کنید"},
    )
    body = forms.CharField(
        label="متن نظر",
        max_length=BODY_MAX,
        widget=FaTextarea(attrs={"class": "textarea w-full", "rows": 4}),
        error_messages={
            "required": "متن نظر را بنویسید",
            "max_length": "متن نظر نباید از ۱۵۰۰ نویسه بیشتر باشد",
        },
    )

    def clean_body(self) -> str:
        # normalize_fa collapses all whitespace, so it runs per line to keep the paragraphs.
        lines = [normalize_fa(line) for line in self.cleaned_data["body"].splitlines()]
        body = _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
        if len(body) < BODY_MIN:
            raise forms.ValidationError("متن نظر دست‌کم ۱۰ نویسه باشد")
        return body
