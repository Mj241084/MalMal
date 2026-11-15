"""Tests for Jalali calendar conversion and form fields (docs/06-jalali-calendar.md section 9.1)."""

from datetime import UTC, date, datetime

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.core.jalali import jalali_str
from apps.core.jalali_forms import JalaliDateField, JalaliDateTimeField, parse_jalali_safe


class JalaliTests(SimpleTestCase):
    def test_str(self):
        self.assertEqual(jalali_str(date(2026, 3, 21)), "۱۴۰۵/۰۱/۰۱")
        aware = datetime(2026, 9, 20, 21, 0, tzinfo=UTC)  # ۰۰:۳۰ تهران، روز بعد
        self.assertEqual(jalali_str(aware), "۱۴۰۵/۰۶/۳۰ ۰۰:۳۰")
        self.assertEqual(jalali_str(None), "")
        self.assertEqual(jalali_str(date(2026, 3, 21), persian=False), "1405/01/01")

    def test_parse_digits_and_separators(self):
        f = JalaliDateField()
        self.assertEqual(f.to_python("۱۴۰۵/۰۶/۳۰"), date(2026, 9, 21))
        self.assertEqual(f.to_python("1405-06-30"), date(2026, 9, 21))
        self.assertEqual(f.to_python("١٤٠٥/٠٦/٣٠"), date(2026, 9, 21))  # ارقام عربی
        self.assertIsNone(f.to_python(""))

    def test_invalid(self):
        f = JalaliDateField()
        for bad in ("۱۴۰۵/۱۳/۰۱", "۱۴۰۵/۰۷/۳۱", "abc", "۱۴۰۵/۰۶", "۱۴۰۵/۰۶/۳۰/۱", "۱۴۰۴/۱۲/۳۰"):
            with self.assertRaises(ValidationError, msg=bad):
                f.to_python(bad)

    def test_leap_esfand(self):
        f = JalaliDateField()
        self.assertEqual(f.to_python("۱۴۰۳/۱۲/۳۰"), date(2025, 3, 20))  # ۱۴۰۳ کبیسه است

    def test_roundtrip_and_has_changed(self):
        f = JalaliDateField()
        self.assertEqual(f.prepare_value(date(2026, 9, 21)), "۱۴۰۵/۰۶/۳۰")
        self.assertFalse(f.has_changed(date(2026, 9, 21), "۱۴۰۵/۰۶/۳۰"))
        self.assertTrue(f.has_changed(date(2026, 9, 21), "۱۴۰۵/۰۶/۲۹"))

    def test_datetime_field(self):
        f = JalaliDateTimeField()
        got = f.to_python("۱۴۰۵/۰۶/۳۰ ۰۰:۳۰")
        self.assertEqual(got.astimezone(UTC), datetime(2026, 9, 20, 21, 0, tzinfo=UTC))
        with self.assertRaises(ValidationError):
            f.to_python("۱۴۰۵/۰۶/۳۰ ۲۵:۰۰")

    def test_parse_jalali_safe(self):
        self.assertEqual(parse_jalali_safe("۱۴۰۵/۰۶/۳۰"), date(2026, 9, 21))
        self.assertIsNone(parse_jalali_safe(""))
        self.assertIsNone(parse_jalali_safe("invalid"))
        self.assertIsNone(parse_jalali_safe("۰۹۰۰/۰۱/۰۱"))
