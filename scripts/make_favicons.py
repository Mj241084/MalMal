#!/usr/bin/env python3
"""Build the favicon / PWA icon set from the (temporary) brand logo.

Usage:  python make_favicons.py static/logo.webp static/favicon

Needs only Pillow. Re-run whenever the logo changes. Output files are generated:
never edit them by hand.

Design rules (why the output looks the way it does):
- The logo is dark on transparent. Browser tabs can be dark, so every icon gets a
  solid light background; a transparent favicon would vanish in dark mode.
- Logo is cropped to its visible bounds, then centred with padding.
- maskable icon keeps the logo inside the central safe zone (OS may crop to a circle).
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BG = (255, 255, 255, 255)  # icon tile background (solid white for legibility in dark tabs)
THEME = "#f7f4ee"  # manifest theme/background colour (base-200 light)
NAME, SHORT = "مل‌مل", "مل‌مل"


def load_logo(path):
    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return im.crop(bbox) if bbox else im


def tile(logo, size, fill=0.78, rounded=0.0, bg=BG):
    """Square icon: solid bg, logo scaled to `fill` of the side, centred."""
    big = size * 4  # draw 4x, downsample once for clean edges
    canvas = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    if rounded:
        d.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(big * rounded), fill=bg)
    else:
        d.rectangle([0, 0, big - 1, big - 1], fill=bg)
    scale = big * fill / max(logo.size)
    lw, lh = max(1, round(logo.width * scale)), max(1, round(logo.height * scale))
    lg = logo.resize((lw, lh), Image.LANCZOS)
    canvas.alpha_composite(lg, ((big - lw) // 2, (big - lh) // 2))
    return canvas.resize((size, size), Image.LANCZOS)


def main(src, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    logo = load_logo(src)
    files = {}
    # tab icons: rounded corners, tight padding so the mark stays readable at 16px
    for s in (16, 32, 48):
        tile(logo, s, fill=0.90, rounded=0.18).save(out / f"favicon-{s}x{s}.png")
        files[f"favicon-{s}x{s}.png"] = s
    tile(logo, 256, fill=0.90, rounded=0.18).save(out / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    # iOS fills transparency with black, so full-bleed opaque, no rounding (iOS rounds it)
    tile(logo, 180, fill=0.78).convert("RGB").save(out / "apple-touch-icon.png")
    tile(logo, 192, fill=0.78).save(out / "icon-192.png")
    tile(logo, 512, fill=0.78).save(out / "icon-512.png")
    tile(logo, 512, fill=0.56).save(out / "icon-maskable-512.png")  # safe zone for circular masks
    # default social-share image (placeholder): logo on warm light field (base-200)
    og = Image.new("RGBA", (1200, 630), (247, 244, 238, 255))
    lg = tile(logo, 420, fill=0.9, rounded=0.1)
    og.alpha_composite(lg, ((1200 - 420) // 2, (630 - 420) // 2))
    og.convert("RGB").save(out / "og-default.png", optimize=True)
    manifest = {
        "name": NAME,
        "short_name": SHORT,
        "lang": "fa",
        "dir": "rtl",
        "start_url": "/",
        "display": "browser",
        "theme_color": THEME,
        "background_color": THEME,
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (out / "site.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
