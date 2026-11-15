"""Admin forms: Jalali day pickers for banner and collection scheduling (docs/06 §8)."""

from __future__ import annotations

from django import forms

from apps.core.jalali_admin import EndOfDayJalaliDateTimeField, JalaliDateWidget
from apps.core.jalali_forms import JalaliDateTimeField
from apps.marketing.models import Banner, Collection


class _ScheduledForm(forms.ModelForm):
    starts_at = JalaliDateTimeField(
        required=False,
        label="شروع نمایش",
        widget=JalaliDateWidget(),
        help_text="خالی = از همین حالا. فقط روز انتخاب می‌شود (ساعت ۰۰:۰۰).",
    )
    ends_at = EndOfDayJalaliDateTimeField(
        required=False,
        label="پایان نمایش",
        widget=JalaliDateWidget(),
        help_text="خالی = بدون پایان. ساعت پایان ۲۳:۵۹ همان روز است.",
    )


class BannerAdminForm(_ScheduledForm):
    class Meta:
        model = Banner
        fields = "__all__"


class CollectionAdminForm(_ScheduledForm):
    class Meta:
        model = Collection
        fields = "__all__"
