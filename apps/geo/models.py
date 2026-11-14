"""Province and city reference data (docs/03 §3, D15)."""

from __future__ import annotations

from django.db import models


class Province(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name="نام استان")
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True, verbose_name="نشانی (slug)")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ["sort", "name"]

    def __str__(self) -> str:
        return self.name


class City(models.Model):
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name="cities",
        verbose_name="استان",
    )
    name = models.CharField(max_length=100, verbose_name="نام شهر")
    slug = models.SlugField(max_length=120, allow_unicode=True, verbose_name="نشانی (slug)")

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["province", "slug"], name="unique_city_slug_per_province"),
        ]
        indexes = [
            models.Index(fields=["province", "name"], name="geo_city_prov_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.province.name})"
