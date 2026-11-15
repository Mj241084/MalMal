"""Engagement models: likes, reviews and the daily purchase ledger (docs/03 §3)."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class Like(models.Model):
    """One heart per (user, product). `Product.like_count` follows through the signals in apps.py."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes", verbose_name="کاربر"
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="likes", verbose_name="محصول")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="uniq_like_user_product")]
        indexes = [models.Index(fields=["product"], name="like_product_idx")]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.product_id}"


class Review(TimeStampedModel):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "در انتظار تایید"),
        (APPROVED, "تاییدشده"),
        (REJECTED, "تایید نشد"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews", verbose_name="کاربر"
    )
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="reviews", verbose_name="محصول"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="امتیاز"
    )
    body = models.TextField(verbose_name="متن نظر")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, verbose_name="وضعیت")
    is_verified_buyer = models.BooleanField(default=False, verbose_name="خریدار محصول")
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    moderated_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان بررسی")
    rejection_reason = models.CharField(max_length=200, blank=True, verbose_name="دلیل رد (داخلی)")
    admin_reply = models.TextField(blank=True, verbose_name="پاسخ فروشگاه")

    class Meta:
        verbose_name = "نظر"
        verbose_name_plural = "نظرها"
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="uniq_review_user_product"),
            models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="review_rating_1_5"),
        ]
        indexes = [models.Index(fields=["product", "status", "-created_at"], name="review_product_status_idx")]

    def __str__(self) -> str:
        return f"{self.product_id} ★{self.rating} ({self.status})"


class ProductDailyStat(models.Model):
    """Purchases per product per local day: the source of the rolling 30-day counter."""

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="+")
    date = models.DateField()
    purchases = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "آمار روزانه‌ی محصول"
        verbose_name_plural = "آمار روزانه‌ی محصولات"
        constraints = [models.UniqueConstraint(fields=["product", "date"], name="uniq_stat_product_date")]
        indexes = [models.Index(fields=["date"], name="stat_date_idx")]
