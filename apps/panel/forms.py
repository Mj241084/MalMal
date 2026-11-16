from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_iran_mobile
from apps.panel.fields import FaIntegerField


class PanelLoginForm(forms.Form):
    mobile = forms.CharField(
        label=_("موبایل"),
        widget=forms.TextInput(attrs={"class": "input w-full text-start", "placeholder": "۰۹..."}),
        validators=[validate_iran_mobile],
    )
    password = forms.CharField(
        label=_("رمز عبور"),
        widget=forms.PasswordInput(attrs={"class": "input w-full text-start"}),
    )


class PasswordChangeForm(forms.Form):
    old = forms.CharField(label=_("رمز فعلی"), widget=forms.PasswordInput(attrs={"class": "input w-full"}))
    new1 = forms.CharField(label=_("رمز جدید"), widget=forms.PasswordInput(attrs={"class": "input w-full"}))
    new2 = forms.CharField(label=_("تکرار رمز"), widget=forms.PasswordInput(attrs={"class": "input w-full"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("new1") != cleaned.get("new2"):
            raise forms.ValidationError("رمزها مطابقت ندارند")
        return cleaned


class SearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-sm w-full",
                "placeholder": "جستجو...",
                "data-hx-get": "/panel/search/",
                "data-hx-trigger": "input changed delay:300ms, search",
                "data-hx-target": "#search-results",
            }
        ),
    )
