from datetime import date, datetime

import jdatetime
from django.utils import timezone

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa_digits(value):
    if value is None:
        return ""
    return str(value).translate(_FA)


def jalali_str(value, fmt=None, persian=True):
    """date یا datetime میلادی ← رشته‌ی شمسی. خالی ← ''.
    datetime آگاه از منطقه‌ی زمانی ابتدا به زمان محلی (تهران) برده می‌شود.
    fmt فقط با کدهای عددی (%Y %m %d %H %M %S) استفاده شود؛ نام ماه وابسته به locale است."""
    if not value:
        return ""
    if isinstance(value, datetime):  # datetime زیرکلاس date است؛ ترتیب شرط‌ها مهم است
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        out = jdatetime.datetime.fromgregorian(datetime=value).strftime(fmt or "%Y/%m/%d %H:%M")
    elif isinstance(value, date):
        out = jdatetime.date.fromgregorian(date=value).strftime(fmt or "%Y/%m/%d")
    else:
        return str(value)
    return to_fa_digits(out) if persian else out
