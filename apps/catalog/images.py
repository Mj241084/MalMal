"""WebP renditions and upload checks for catalog images (docs/phases P1 task 10, P11)."""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, ImageOps

from apps.catalog.constants import IMAGE_WIDTHS
from apps.core.jalali import to_fa_digits

logger = logging.getLogger(__name__)

UPLOAD_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def generate_webp_sizes(image_field, widths: tuple[int, ...] = IMAGE_WIDTHS) -> dict[str, str]:
    """Generate resized WebP files and return ``{width: relative path}``."""
    source = Path(image_field.path)
    with Image.open(source) as opened:
        # Phone photos store their rotation in EXIF; without this the renditions come out sideways.
        image = ImageOps.exif_transpose(opened).convert("RGB")
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


def validate_upload(file, *, max_bytes: int, label: str = "تصویر") -> tuple[str, int, int]:
    """Check an uploaded image. Returns (extension, width, height) or raises ValidationError with a Persian message."""
    if file.size > max_bytes:
        raise ValidationError(f"حجم {label} نباید بیشتر از {to_fa_digits(max_bytes // (1024 * 1024))} مگابایت باشد")
    try:
        file.seek(0)
        with Image.open(file) as probe:
            probe.verify()
        file.seek(0)
        with Image.open(file) as image:
            image_format, (width, height) = image.format, image.size
    except Exception as exc:  # Pillow raises several unrelated types for broken or hostile files
        raise ValidationError(f"{label} معتبر نیست") from exc
    finally:
        file.seek(0)
    if image_format not in UPLOAD_FORMATS:
        raise ValidationError(f"{label} باید jpg، png یا webp باشد")
    return UPLOAD_FORMATS[image_format], width, height
