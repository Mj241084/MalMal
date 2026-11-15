"""Cart models: one server cart per user, lines reference variants only (D16)."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self) -> str:
        return f"سبد {self.user}"


class CartItem(TimeStampedModel):
    """Only (variant, qty): prices and stock are always re-read (D16)."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.Variant", on_delete=models.CASCADE, related_name="+")
    qty = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "قلم سبد"
        verbose_name_plural = "اقلام سبد"
        ordering = ["pk"]
        constraints = [models.UniqueConstraint(fields=["cart", "variant"], name="uniq_cart_variant")]

    def __str__(self) -> str:
        return f"{self.variant_id} × {self.qty}"
