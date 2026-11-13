from datetime import date, datetime

import jdatetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .jalali import jalali_str

_FA_AR_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_digits_and_separators(val_str):
    """ارقام فارسی و عربی ← لاتین، «-» ← «/»."""
    if not val_str:
        return ""
    return str(val_str).strip().translate(_FA_AR_TO_EN).replace("-", "/")


class JalaliDateField(forms.Field):
    default_error_messages = {
        "invalid": "تاریخ وارد شده نامعتبر است. نمونه صحیح: ۱۴۰۵/۰۶/۳۰",
    }

    def prepare_value(self, value):
        # برای نمایش مقدار اولیه‌ی فرم
        if isinstance(value, (datetime, date)):
            return jalali_str(value, fmt="%Y/%m/%d", persian=True)
        return value or ""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        parts = normalize_digits_and_separators(value).split("/")
        if len(parts) != 3:
            raise ValidationError(self.error_messages["invalid"], code="invalid")
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return jdatetime.date(year, month, day).togregorian()  # ماه ۱۳، روز ۳۱ مهر، ۳۰ اسفند غیرکبیسه ← ValueError
        except (ValueError, TypeError, OverflowError):
            raise ValidationError(self.error_messages["invalid"], code="invalid")  # noqa: B904

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        try:
            data_val = self.to_python(data)
        except ValidationError:
            return True
        return self.to_python(initial) != data_val


class JalaliDateTimeField(forms.Field):
    """تاریخ و ساعت متنی («۱۴۰۵/۰۶/۳۰ ۱۴:۳۰»). خروجی datetime آگاه از منطقه‌ی زمانی (تهران)."""

    default_error_messages = {
        "invalid": "تاریخ و ساعت وارد شده نامعتبر است. نمونه صحیح: ۱۴۰۵/۰۶/۳۰ ۱۴:۳۰",
    }

    def prepare_value(self, value):
        if isinstance(value, datetime):
            return jalali_str(value, fmt="%Y/%m/%d %H:%M", persian=True)
        if isinstance(value, date):
            return jalali_str(value, fmt="%Y/%m/%d", persian=True)
        return value or ""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime):
            return timezone.make_aware(value) if timezone.is_naive(value) else value

        tokens = normalize_digits_and_separators(value).split()
        if len(tokens) == 1:
            date_part, time_part = tokens[0], "00:00:00"
        elif len(tokens) == 2:
            date_part, time_part = tokens
        else:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

        d, t = date_part.split("/"), time_part.split(":")
        if len(d) != 3 or len(t) not in (2, 3):
            raise ValidationError(self.error_messages["invalid"], code="invalid")
        try:
            jdt = jdatetime.datetime(
                int(d[0]),
                int(d[1]),
                int(d[2]),
                int(t[0]),
                int(t[1]),
                int(t[2]) if len(t) == 3 else 0,
            )
            return timezone.make_aware(jdt.togregorian(), timezone=timezone.get_current_timezone())
        except (ValueError, TypeError, OverflowError):
            raise ValidationError(self.error_messages["invalid"], code="invalid")  # noqa: B904

    def has_changed(self, initial, data):
        if self.disabled:
            return False
        try:
            data_val = self.to_python(data)
        except ValidationError:
            return True
        initial_val = self.to_python(initial)
        if initial_val is None and data_val is None:
            return False
        if initial_val is None or data_val is None:
            return True
        return abs((initial_val - data_val).total_seconds()) > 59


def parse_jalali_safe(raw):
    """رشته‌ی شمسی ← date میلادی؛ خالی، نامعتبر یا خارج از ۱۹۰۰ تا ۲۹۹۹ ← None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        day = JalaliDateField().to_python(raw)
    except ValidationError:
        return None
    return day if day and 1900 <= day.year <= 2999 else None
