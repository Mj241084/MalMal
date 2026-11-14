"""SMS log model (docs/03 §3, docs/05 §4)."""

from __future__ import annotations

from django.db import models


class SmsLog(models.Model):
    """Append-only record of every SMS attempt. Never stores OTP codes or secrets."""

    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED_NO_TEMPLATE = "skipped_no_template"
    STATUS_CHOICES = [
        (STATUS_SENT, "ارسال شد"),
        (STATUS_FAILED, "ناموفق"),
        (STATUS_SKIPPED_NO_TEMPLATE, "بدون شناسه قالب"),
    ]

    mobile = models.CharField(max_length=11, verbose_name="موبایل گیرنده")
    kind = models.CharField(max_length=40, db_index=True, verbose_name="کلید قالب")
    provider_message_id = models.CharField(max_length=80, blank=True, verbose_name="شناسه پیامک سرویس‌دهنده")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, verbose_name="وضعیت")
    error = models.TextField(blank=True, verbose_name="خطا")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="زمان")

    class Meta:
        verbose_name = "لاگ پیامک"
        verbose_name_plural = "لاگ‌های پیامک"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["mobile", "-created_at"], name="smslog_mobile_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind} → {self.mobile} ({self.get_status_display()})"
