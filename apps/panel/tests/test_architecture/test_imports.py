"""D35: only apps/panel may import apps.panel."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
IMPORT = re.compile(r"^\s*(from\s+apps\.panel|import\s+apps\.panel)", re.M)


def test_only_the_panel_imports_the_panel():
    offenders = [
        str(path.relative_to(ROOT))
        for folder in ("apps", "config", "scripts")
        for path in (ROOT / folder).rglob("*.py")
        if "apps/panel/" not in path.as_posix() and IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders
