import pytest
import pathlib
import re

def test_no_forbidden_imports():
    root = pathlib.Path(".")
    offenders = []
    
    # regex to find imports of apps.panel
    panel_import_re = re.compile(r"from\s+apps\.panel|import\s+apps\.panel")
    
    for path in root.rglob("*.py"):
        if path.parts[0] in ["apps", "config", "scripts", "templates"]:
            if "apps/panel/" in str(path).replace("\\", "/"):
                continue
                
            content = path.read_text(encoding="utf-8")
            if panel_import_re.search(content):
                offenders.append(str(path))
                
    assert not offenders, f"Only apps/panel may import apps/panel (D35):\n" + "\n".join(offenders)
