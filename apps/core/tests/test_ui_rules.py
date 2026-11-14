import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
NATIVE = re.compile(r"(?<![\w.$])(?:alert|confirm|prompt)\s*\(|window\.(?:alert|confirm|prompt)\b")


def _sources():
    for pattern in ("templates/**/*.html", "static/js/**/*.js"):
        for path in BASE.glob(pattern):
            if path.name == "htmx.min.js":
                continue
            yield path


def test_no_native_browser_dialogs():
    offenders = [
        f"{path.relative_to(BASE)}:{number}"
        for path in _sources()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if NATIVE.search(line)
    ]
    assert not offenders, "Use MM.ui.confirm/alert/toast (docs/08-ui-modules.md):\n" + "\n".join(offenders)


def test_every_mm_module_is_documented():
    doc = (BASE / "docs" / "08-ui-modules.md").read_text(encoding="utf-8")
    for path in (BASE / "static" / "js" / "mm").glob("*.js"):
        assert path.name in doc, f"{path.name} is missing from docs/08-ui-modules.md"
