#!/usr/bin/env python3
"""Build an optimized SVG icon sprite from static/src/sprite.svg.

Scans Django templates for `{% icon "name" ... %}` usages (plus any always-included
icons) and writes only the referenced <symbol> definitions to static/sprite.svg.

Usage:
    uv run python scripts/build_sprite.py
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_SPRITE = ROOT / "static" / "src" / "sprite.svg"
OUT_SPRITE = ROOT / "static" / "sprite.svg"
SCAN_DIRS = [ROOT / "templates", ROOT / "apps"]

ICON_RE = re.compile(r"""\{%\s*icon\s+["']([a-z0-9-]+)["']""")
NAV_ICON_RE = re.compile(r"""\bicon\s*=\s*["']([a-z0-9-]+)["']""")  # NavItem(icon="...") in apps/panel
SVG_NS = "http://www.w3.org/2000/svg"

# Icons referenced dynamically (e.g. TrustItem seed or JS states) can be listed here.
ALWAYS_INCLUDE: set[str] = {
    "alert-circle",
    "check",
    "info",
    "x",
    # TrustItem icons live in the database, so the template scan cannot see them.
    "lock",
    "phone",
    "shield-check",
    "truck",
    "menu",
    "search",
    "shopping-bag",
    "credit-card",
    "copy",
    "printer",
    "arrow-left",
    "user",
    "log-out",
    "package",
}


def collect_used_icons() -> set[str]:
    names = set(ALWAYS_INCLUDE)
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for ext in ("*.html", "*.py"):
            for path in base.rglob(ext):
                # Tests reference deliberately missing icon names, which are not real usages.
                if "tests" in path.parts or path.name.startswith("test_"):
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                names.update(ICON_RE.findall(text))
                if path.suffix == ".py" and "panel" in path.parts:
                    names.update(NAV_ICON_RE.findall(text))
    return names


def build_sprite(used: set[str] | None = None) -> tuple[Path, int, list[str]]:
    if not SRC_SPRITE.exists():
        raise FileNotFoundError(f"Source sprite not found: {SRC_SPRITE}")

    if used is None:
        used = collect_used_icons()

    ET.register_namespace("", SVG_NS)
    tree = ET.parse(SRC_SPRITE)
    root = tree.getroot()

    symbol_map: dict[str, ET.Element] = {}
    for elem in root:
        local = elem.tag.split("}")[-1]
        if local == "symbol" and "id" in elem.attrib:
            symbol_map[elem.attrib["id"]] = elem

    missing = sorted(name for name in used if name not in symbol_map)

    out_root = ET.Element(f"{{{SVG_NS}}}svg", {"style": "display: none;"})
    included = 0
    for name in sorted(used):
        sym = symbol_map.get(name)
        if sym is None:
            continue
        # Remove hardcoded stroke-width="2" and fill="none" from the source symbol: the outer <svg>
        # sets stroke-width="1.5" and fill="none", so a filled state (fill-current) can win.
        new_attrib = {k: v for k, v in sym.attrib.items() if k not in ("stroke-width", "fill")}
        new_sym = ET.Element(f"{{{SVG_NS}}}symbol", new_attrib)
        for child in sym:
            # Strip comments and copy geometry elements cleanly.
            if callable(child.tag):
                continue
            new_sym.append(child)
        out_root.append(new_sym)
        included += 1

    out_tree = ET.ElementTree(out_root)
    ET.indent(out_tree, space="  ")
    OUT_SPRITE.parent.mkdir(parents=True, exist_ok=True)
    out_tree.write(OUT_SPRITE, encoding="utf-8", xml_declaration=False)
    return OUT_SPRITE, included, missing


def main() -> int:
    used = collect_used_icons()
    out_path, included, missing = build_sprite(used)
    print(f"Wrote {out_path.relative_to(ROOT)} with {included} icon(s).")
    if missing:
        print(f"ERROR: Missing icon(s) in {SRC_SPRITE.name}: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
