"""Small catalog helpers."""

from __future__ import annotations

from django.utils.text import slugify


def unique_slug(instance, source: str, field: str = "slug", max_length: int = 180) -> str:
    """Build a unique (Unicode-aware) slug for ``instance`` from ``source``."""
    base = slugify(source, allow_unicode=True)[:max_length] or "item"
    model = instance.__class__
    candidate = base
    suffix = 2
    while model.objects.exclude(pk=instance.pk).filter(**{field: candidate}).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate
