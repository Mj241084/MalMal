"""Architecture guard: raw ``update()`` must not bypass cache revision tracking (docs/03 §5)."""

from __future__ import annotations

import re
from pathlib import Path

APPS_DIR = Path(__file__).resolve().parents[2]
ALLOWED_FILES = {
    "apps/catalog/cache.py",
    "apps/catalog/tree.py",
    "apps/catalog/models.py",
    "apps/catalog/stock.py",
    "apps/engagement/counters.py",
}
PATTERN = re.compile(r"(Product|Variant|Category)\.objects[^\n]*?\.update\(")


def test_no_raw_queryset_update_on_tracked_models():
    offenders = []
    for path in APPS_DIR.rglob("*.py"):
        relative = path.relative_to(APPS_DIR.parent).as_posix()
        if relative in ALLOWED_FILES or "/migrations/" in relative or "/tests/" in relative:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if PATTERN.search(line):
                offenders.append(f"{relative}:{number}: {line.strip()}")

    assert not offenders, "Use update_tracked()/bulk_update_tracked() instead:\n" + "\n".join(offenders)
