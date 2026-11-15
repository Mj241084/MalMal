"""Minimal whitelist HTML sanitizer for admin-authored rich text.

Product descriptions are written by staff, but stored HTML is still untrusted:
only a small set of formatting tags survives, and all attributes except ``href``
on links are dropped. No third-party dependency is needed for this.
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "h2", "h3", "h4", "a", "blockquote"}
VOID_TAGS = {"br"}
ALLOWED_ATTRS = {"a": {"href"}}

_SCHEME = re.compile(r"^([a-z][a-z0-9+.\-]*):", re.I)
ALLOWED_SCHEMES = {"http", "https", "mailto", "tel"}

# Every <a> gets these: a link into a product description is never a popup with an opener handle.
LINK_REL = "noopener noreferrer"


def _safe_href(value: str) -> str | None:
    # browsers ignore tabs, newlines and C0 controls inside a URL, so compare on the compacted value
    compact = "".join(ch for ch in value if ord(ch) > 32 and ord(ch) != 127)
    if not compact or compact.startswith("//"):
        return None
    match = _SCHEME.match(compact)
    if match and match.group(1).lower() not in ALLOWED_SCHEMES:
        return None
    return compact


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag not in ALLOWED_TAGS:
            return
        allowed = ALLOWED_ATTRS.get(tag, set())
        rendered = []
        for name, value in attrs:
            if name not in allowed or not value:
                continue
            if name == "href":
                value = _safe_href(value)
                if value is None:
                    continue
            rendered.append(f' {name}="{escape(value, quote=True)}"')
        if tag == "a":
            rendered.append(f' rel="{LINK_REL}"')
        self.parts.append(f"<{tag}{''.join(rendered)}>")

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data, quote=False))


def sanitize_html(value: str | None) -> str:
    """Return ``value`` with only whitelisted tags and no event handlers."""
    if not value:
        return ""
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)
