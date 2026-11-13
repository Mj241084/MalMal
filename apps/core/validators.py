"""Iranian national code and mobile number validators."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

from apps.core.text import normalize_digits

_MOBILE_RE = re.compile(r"^09\d{9}$")
_STRIP_MOBILE_RE = re.compile(r"[\s\-().]+")


def normalize_national_code(value: str | None) -> str:
    """Normalize digits and whitespace for a national code."""
    return normalize_digits(value or "").strip()


def validate_national_code(value: str | None) -> str:
    """Validate Iranian 10-digit national code with checksum and reject repeated digits."""
    code = normalize_national_code(value)
    if len(code) != 10 or not code.isdigit():
        raise ValidationError("کد ملی باید دقیقاً ۱۰ رقم باشد.", code="invalid_national_code")
    if len(set(code)) == 1:
        raise ValidationError("کد ملی وارد‌شده معتبر نیست.", code="invalid_national_code")

    checksum = sum(int(code[i]) * (10 - i) for i in range(9))
    rem = checksum % 11
    check_digit = int(code[9])
    valid = (rem < 2 and check_digit == rem) or (rem >= 2 and check_digit == 11 - rem)
    if not valid:
        raise ValidationError("کد ملی وارد‌شده معتبر نیست.", code="invalid_national_code")
    return code


def normalize_iran_mobile(value: str | None) -> str:
    """Normalize Iranian mobile input to `09XXXXXXXXX` (raises ValidationError if invalid)."""
    raw = _STRIP_MOBILE_RE.sub("", normalize_digits(value or ""))
    if raw.startswith("+98"):
        raw = "0" + raw[3:]
    elif raw.startswith("0098"):
        raw = "0" + raw[4:]
    elif raw.startswith("98") and len(raw) == 12:
        raw = "0" + raw[2:]
    elif raw.startswith("9") and len(raw) == 10:
        raw = "0" + raw

    if not _MOBILE_RE.match(raw):
        raise ValidationError(
            "شماره‌ی موبایل باید با ۰۹ شروع شود و ۱۱ رقم باشد.",
            code="invalid_mobile",
        )
    return raw


def validate_iran_mobile(value: str | None) -> str:
    """Django validator wrapper returning normalized `09XXXXXXXXX` or raising ValidationError."""
    return normalize_iran_mobile(value)
