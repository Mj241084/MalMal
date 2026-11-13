"""Tests for Persian normalization, currency formatting, and Iranian validators."""

import pytest
from django.core.exceptions import ValidationError
from django.template import Context, Template

from apps.core.text import format_toman, normalize_digits, normalize_fa
from apps.core.validators import normalize_iran_mobile, validate_national_code


def _make_valid_national_code(first_nine: str) -> str:
    s = sum(int(first_nine[i]) * (10 - i) for i in range(9))
    rem = s % 11
    check = rem if rem < 2 else 11 - rem
    return first_nine + str(check)


class TestNormalizeFa:
    def test_arabic_letters_diacritics_kashida_and_digits(self):
        raw = "  كيـف  مَدرسة  ۱۲۳٤٥  "
        assert normalize_fa(raw) == "کیف مدرسه 12345"

    def test_preserves_zwnj_in_input_mode_and_splits_in_search_mode(self):
        assert normalize_fa("ماشین‌لباس‌شویی   Bosch") == "ماشین‌لباس‌شویی Bosch"
        assert normalize_fa("ماشین‌لباس‌شویی   Bosch", for_search=True) == "ماشین لباس شویی bosch"

    def test_empty_and_none(self):
        assert normalize_fa("") == ""
        assert normalize_fa(None) == ""
        assert normalize_digits(None) == ""


class TestTomanFormatting:
    def test_format_toman_values(self):
        assert format_toman(1250000) == "۱٬۲۵۰٬۰۰۰"
        assert format_toman(0) == "۰"
        assert format_toman(-5000) == "-۵٬۰۰۰"
        assert format_toman(None) == ""

    def test_toman_template_filter(self):
        tpl = Template("{% load core_tags %}{{ price|toman }} تومان")
        assert tpl.render(Context({"price": 1250000})) == "۱٬۲۵۰٬۰۰۰ تومان"


class TestNationalCodeValidator:
    def test_accepts_valid_and_persian_digits(self):
        valid_code = _make_valid_national_code("001352084")
        assert validate_national_code(valid_code) == valid_code
        persian_code = valid_code.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        assert validate_national_code(persian_code) == valid_code

    @pytest.mark.parametrize("bad", ["", "123", "12345678901", "abcdefghij", "1111111111", "0000000000"])
    def test_rejects_malformed_and_repeated_digits(self, bad):
        with pytest.raises(ValidationError):
            validate_national_code(bad)

    def test_rejects_invalid_checksum(self):
        valid_code = _make_valid_national_code("049937089")
        wrong_last = str((int(valid_code[-1]) + 1) % 10)
        with pytest.raises(ValidationError):
            validate_national_code(valid_code[:9] + wrong_last)


class TestIranMobileValidator:
    @pytest.mark.parametrize(
        "raw",
        [
            "09123456789",
            "۰۹۱۲۳۴۵۶۷۸۹",
            "+989123456789",
            "00989123456789",
            "989123456789",
            "9123456789",
            "0912-345-6789",
            " ٠٩١٢ ٣٤٥ ٦٧٨٩ ",
        ],
    )
    def test_normalizes_valid_iran_mobile(self, raw):
        assert normalize_iran_mobile(raw) == "09123456789"

    @pytest.mark.parametrize("bad", ["", "02112345678", "0912345678", "091234567890", "08123456789", "abc"])
    def test_rejects_invalid_mobile(self, bad):
        with pytest.raises(ValidationError):
            normalize_iran_mobile(bad)
