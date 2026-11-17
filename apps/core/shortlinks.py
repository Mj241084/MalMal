"""Stateless short links for SMS (#LINK# must stay <= 25 characters).

A code is `<kind><pk in base36>`: `p3a7` is product 4,279. Nothing is stored, so nothing accumulates, and the
redirect always lands on the product's *current* canonical URL even after its slug changes.
"""

from __future__ import annotations

import re

from django.conf import settings

MAX_PARAM_LENGTH = 25
# kind letter -> (app_label, model_name). Add a row when another object type needs SMS links.
KINDS: dict[str, tuple[str, str]] = {"p": ("catalog", "Product")}

_CODE_RE = re.compile(r"^(?P<kind>[a-z])(?P<body>[0-9a-z]{1,10})$")
_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _to_base36(number: int) -> str:
    if number < 0:
        raise ValueError("pk must be positive")
    out = ""
    while True:
        number, remainder = divmod(number, 36)
        out = _DIGITS[remainder] + out
        if not number:
            return out


def encode(kind: str, pk: int) -> str:
    if kind not in KINDS:
        raise ValueError(f"Unknown short-link kind: {kind!r}")
    return f"{kind}{_to_base36(int(pk))}"


def decode(code: str) -> tuple[str, int]:
    match = _CODE_RE.match(code or "")
    if match is None or match["kind"] not in KINDS:
        raise ValueError(f"Invalid short-link code: {code!r}")
    return match["kind"], int(match["body"], 36)


def short_link_param(kind: str, pk: int) -> str:
    """Return `r/<code>` for the `#LINK#` SMS parameter."""
    param = f"r/{encode(kind, pk)}"
    if len(param) > MAX_PARAM_LENGTH:
        raise ValueError(f"Short link exceeds {MAX_PARAM_LENGTH} characters: {param!r}")
    return param


def short_url(kind: str, pk: int) -> str:
    """Absolute link for people (copy/share): SITE_URL/r/<code>/. The trailing slash avoids an APPEND_SLASH redirect hop."""
    return f"{settings.SITE_URL}/{short_link_param(kind, pk)}/"
