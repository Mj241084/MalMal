#!/usr/bin/env python3
"""Turn the raw social logos in static/img/*.png into small lossless WebP icons in static/img/social/.

Re-run whenever a logo changes: drop the PNG into static/img/ and run
    uv run python scripts/optimize_social_icons.py
The PNG is moved to assets-incoming/social-originals/ (git-ignored) after a successful conversion.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "static" / "img"
OUT = SRC / "social"
ARCHIVE = ROOT / "assets-incoming" / "social-originals"
SIZE = 96  # shown at 24px; 96 covers a 4x screen
NAMES = {"X_Twitter": "x"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC.glob("*.png")):
        name = NAMES.get(path.stem, path.stem.lower())
        target = OUT / f"{name}.webp"
        with Image.open(path) as opened:
            image = opened.convert("RGBA")
            image.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
            image.save(target, "WEBP", lossless=True, method=6)
        print(f"{path.name} ({path.stat().st_size // 1024} KB) -> {target.name} ({target.stat().st_size // 1024} KB)")
        shutil.move(str(path), ARCHIVE / path.name)


if __name__ == "__main__":
    main()
