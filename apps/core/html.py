"""Minimal whitelist HTML sanitizer for admin-authored rich text.

Product descriptions are written by staff, but stored HTML is still untrusted:
only a small set of formatting tags survives, and all attributes except ``href``
on links are dropped. No third-party dependency is needed for this.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "h2", "h3", "h4", "a", "blockquote"}
VOID_TAGS = {"br"}
ALLOWED_ATTRS = {"a": {"href"}}


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
            if name in allowed and value:
                if name == "href" and value.strip().lower().startswith(("javascript:", "data:")):
                    continue
                rendered.append(f' {name}="{escape(value, quote=True)}"')
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
