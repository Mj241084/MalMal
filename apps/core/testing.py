"""Test helpers shared across apps."""

from __future__ import annotations

import re
from html.parser import HTMLParser

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_DIGIT = re.compile(r"[0-9]")
_LATIN = re.compile(r"[A-Za-z]")


class _Scanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, bool]] = []
        self.ascii_text: list[str] = []
        self.ascii_inputs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and "data-fa-digits" in attributes and _DIGIT.search(attributes.get("value") or ""):
            self.ascii_inputs.append(attributes.get("name") or "?")
        if tag in _VOID:
            return
        exempt = (
            tag in {"script", "style"}
            or "latin" in (attributes.get("class") or "").split()
            or "data-ascii" in attributes
        )
        self._stack.append((tag, exempt))

    def handle_endtag(self, tag):
        if any(open_tag == tag for open_tag, _ in self._stack):
            while self._stack.pop()[0] != tag:
                pass

    def handle_data(self, data):
        if any(exempt for _, exempt in self._stack):
            return
        for token in data.split():
            if _DIGIT.search(token) and not _LATIN.search(token):
                self.ascii_text.append(token)


def find_ascii_digits(html: str) -> tuple[list[str], list[str]]:
    """Return (ASCII digit tokens shown as text, names of digit inputs rendered with ASCII values)."""
    scanner = _Scanner()
    scanner.feed(html)
    return scanner.ascii_text, scanner.ascii_inputs
