"""WebP rendition generation for product images (docs/phases P1 task 10).

Renditions are produced at upload time (``ProductImage.save``) so serving never
does image work. Files land next to the original as ``<stem>-<width>.webp`` and
the model stores ``{width: path_relative_to_MEDIA_ROOT}`` in ``widths``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from PIL import Image

from apps.catalog.constants import IMAGE_WIDTHS

logger = logging.getLogger(__name__)


def generate_webp_sizes(image_field, widths: tuple[int, ...] = IMAGE_WIDTHS) -> dict[str, str]:
    """Generate resized WebP files and return ``{width: relative path}``."""
    source = Path(image_field.path)
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        original_width = image.width
        result: dict[str, str] = {}
        for width in widths:
            if width > original_width * 1.5:
                continue
            height = max(1, round(image.height * width / image.width))
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            target = source.with_name(f"{source.stem}-{width}.webp")
            resized.save(target, format="WEBP", quality=82, method=4)
            result[str(width)] = str(target.relative_to(Path(settings.MEDIA_ROOT))).replace("\\", "/")
    return result
