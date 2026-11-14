"""Persian text normalization and numeric formatting utilities."""

from __future__ import annotations

import re

_DIGITS_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_DIGITS_TO_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_LATIN_RE = re.compile(r"[A-Za-z]")
_SPLIT_WS_RE = re.compile(r"(\s+)")


def to_fa_text(value: object) -> str:
    """Persian digits for free text. Tokens that contain Latin letters (WM-1234, 5kg) stay untouched."""
    if value is None:
        return ""
    return "".join(
        part if _LATIN_RE.search(part) else part.translate(_DIGITS_TO_FA) for part in _SPLIT_WS_RE.split(str(value))
    )


# For general user input: preserve hamza forms (ئ، أ، ؤ) in Persian words like "می‌خواهم", "مسئله", "سؤال".
_GENERAL_CHAR_MAP = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
    }
)

# Arabic diacritics & tatweel (kashida)
_DIACRITICS_AND_TATWEEL_RE = re.compile(r"[ـً-ٰٟۖ-ۭ]")
_WHITESPACE_RE = re.compile(r"\s+")
_MULTI_ZWNJ_RE = re.compile(r"‌+")


def normalize_digits(value: str | int | None) -> str:
    """Convert Persian and Arabic-Indic digits to ASCII 0-9."""
    if value is None:
        return ""
    return str(value).translate(_DIGITS_TO_EN)


def normalize_fa(text: str | None, *, for_search: bool = False) -> str:
    """Normalize Persian/Arabic text for storage, validation, or search.

    - Converts Arabic ي/ى -> ی, ك -> ک, ة -> ه
    - Strips Arabic diacritics and kashida (ـ)
    - Converts Persian/Arabic digits to ASCII 0-9
    - Normalizes ZWNJ (‌): preserved (collapsed) in general mode, replaced with space in search mode
    - Collapses extra whitespace and trims
    - Lowercases Latin characters when `for_search=True`
    """
    if not text:
        return ""
    out = str(text)
    out = _DIACRITICS_AND_TATWEEL_RE.sub("", out)
    out = out.translate(_GENERAL_CHAR_MAP)
    out = out.translate(_DIGITS_TO_EN)

    if for_search:
        out = out.replace("‌", " ").replace("‍", "")
        out = out.lower()
    else:
        out = out.replace("‍", "")
        out = _MULTI_ZWNJ_RE.sub("‌", out)
        # Strip ZWNJ immediately adjacent to whitespace
        out = re.sub(r"\s*‌\s*", lambda m: " " if any(c.isspace() for c in m.group(0)) else "‌", out)

    out = _WHITESPACE_RE.sub(" ", out).strip()
    return out


def format_toman(value: int | str | None) -> str:
    """Format an integer amount in Tomans using Persian digits and U+066C thousands separator."""
    if value is None or value == "":
        return ""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return ""

    sign = "-" if amount < 0 else ""
    formatted = f"{abs(amount):,}".replace(",", "٬").translate(_DIGITS_TO_FA)
    return f"{sign}{formatted}"
