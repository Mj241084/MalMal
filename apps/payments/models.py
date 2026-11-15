"""Payment gateway and payment attempt models (docs/03 §3)."""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class PaymentGateway(TimeStampedModel):
    code = models.SlugField(max_length=32, unique=True, verbose_name="کد")
    title = models.CharField(max_length=120, verbose_name="عنوان")
    logo = models.ImageField(upload_to="gateways/", blank=True, verbose_name="لوگو")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    min_amount = models.BigIntegerField(default=0, verbose_name="حداقل مبلغ (تومان)")
    max_amount = models.BigIntegerField(null=True, blank=True, verbose_name="حداکثر مبلغ (تومان)")

    class Meta:
        verbose_name = "درگاه پرداخت"
        verbose_name_plural = "درگاه‌های پرداخت"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.title

    def accepts(self, amount: int) -> bool:
        return amount >= self.min_amount and (self.max_amount is None or amount <= self.max_amount)


class Payment(TimeStampedModel):
    INITIATED = "initiated"
    REDIRECTED = "redirected"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (INITIATED, "ایجادشده"),
        (REDIRECTED, "ارجاع به درگاه"),
        (VERIFYING, "در حال تایید"),
        (VERIFIED, "تاییدشده"),
        (FAILED, "ناموفق"),
        (CANCELLED, "لغوشده"),
    ]
    # A callback that claimed VERIFYING and then died is put back to REDIRECTED after this long.
    VERIFY_STALE = timedelta(minutes=2)

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments", verbose_name="سفارش")
    gateway_code = models.CharField(max_length=32, verbose_name="درگاه")
    amount = models.BigIntegerField(verbose_name="مبلغ (تومان)")
    authority = models.CharField(max_length=64, blank=True, verbose_name="شناسه مرجع")
    ref_id = models.CharField(max_length=32, blank=True, verbose_name="شماره تراکنش")
    card_pan_masked = models.CharField(max_length=32, blank=True, verbose_name="کارت")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=INITIATED, verbose_name="وضعیت")
    request_payload = models.JSONField(default=dict, blank=True)  # never secrets
    verify_payload = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["gateway_code", "authority"],
                condition=~Q(authority=""),
                name="uniq_payment_gateway_authority",
            )
        ]
        indexes = [models.Index(fields=["order", "status"], name="payment_order_status_idx")]

    def __str__(self) -> str:
        return f"{self.gateway_code}:{self.authority or self.pk} ({self.status})"
