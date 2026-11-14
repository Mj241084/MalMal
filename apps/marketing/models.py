"""Site-wide trust claims shown on product and home pages (docs/03 §3 marketing)."""

from __future__ import annotations

from django.db import models, transaction

from apps.core.models import TimeStampedModel


class TrustItem(TimeStampedModel):
    """A promise the store makes («ارسال به سراسر کشور»، «ضمانت اصالت» …).

    Seeded rows carry ``is_placeholder=True`` because the wording is assumed, not
    confirmed by the owner; ``manage.py check_launch`` warns until they are edited.
    """

    icon = models.CharField(
        max_length=64,
        verbose_name="نام آیکون",
        help_text="نام نماد در sprite (مثلاً truck، shield-check، lock، phone).",
    )
    title = models.CharField(max_length=120, verbose_name="عنوان")
    subtitle = models.CharField(max_length=200, blank=True, verbose_name="توضیح کوتاه")
    is_placeholder = models.BooleanField(
        default=False,
        verbose_name="متن فرضی (placeholder)",
        help_text="تا وقتی روشن است، check_launch هشدار می‌دهد.",
    )
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "مزیت فروشگاه"
        verbose_name_plural = "مزیت‌های فروشگاه"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        transaction.on_commit(self._invalidate_cache)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        transaction.on_commit(self._invalidate_cache)
        return result

    @staticmethod
    def _invalidate_cache() -> None:
        from apps.marketing.cache import bump_trust_revision

        bump_trust_revision()
