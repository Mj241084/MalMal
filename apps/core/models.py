"""Core site configuration, static pages, and footer link models."""

from __future__ import annotations

from django.db import models, transaction

from apps.core.cache import safe_cache_delete, safe_cache_get, safe_cache_incr_epoch, safe_cache_set

SITE_SETTINGS_CACHE_KEY = "site_settings"
FOOTER_LINKS_CACHE_KEY = "footer_links"


class TimeStampedModel(models.Model):
    """Abstract base model with UTC created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="به‌روزرسانی")

    class Meta:
        abstract = True


class SiteSettings(TimeStampedModel):
    """Singleton site configuration editable in Django admin and cached in Redis."""

    store_name = models.CharField(max_length=120, default="مل‌مل", verbose_name="نام فروشگاه")
    logo_light = models.ImageField(upload_to="site/", blank=True, verbose_name="لوگوی تم روشن")
    logo_dark = models.ImageField(upload_to="site/", blank=True, verbose_name="لوگوی تم تاریک")
    phone = models.CharField(max_length=40, blank=True, verbose_name="تلفن")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, verbose_name="آدرس")
    working_hours = models.CharField(max_length=160, blank=True, verbose_name="ساعات پاسخگویی")

    instagram_url = models.URLField(blank=True, verbose_name="اینستاگرام")
    telegram_url = models.URLField(blank=True, verbose_name="تلگرام")
    whatsapp_url = models.URLField(blank=True, verbose_name="واتساپ")
    bale_url = models.URLField(blank=True, verbose_name="بله")
    eitaa_url = models.URLField(blank=True, verbose_name="ایتا")
    igap_url = models.URLField(blank=True, verbose_name="آی‌گپ")
    rubika_url = models.URLField(blank=True, verbose_name="روبیکا")
    soroush_url = models.URLField(blank=True, verbose_name="سروش پلاس")
    x_url = models.URLField(blank=True, verbose_name="ایکس (توییتر)")

    free_shipping_threshold = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="آستانه ارسال رایگان (تومان)",
        help_text="خالی = غیرفعال (در ارسال پس‌کرایه خالی بگذارید).",
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        verbose_name="آستانه هشدار موجودی کم",
    )
    shipping_note = models.CharField(
        max_length=200,
        blank=True,
        default="ارسال با تیپاکس به سراسر کشور؛ کرایه هنگام تحویل به پیک پرداخت می‌شود.",
        verbose_name="متن ارسال در صفحه‌ی محصول",
        help_text="خالی = نمایش داده نمی‌شود. در P3 از ShippingMethod خوانده می‌شود.",
    )

    otp_ttl_seconds = models.PositiveIntegerField(default=120, verbose_name="مدت اعتبار کد تایید (ثانیه)")
    otp_max_attempts = models.PositiveIntegerField(default=5, verbose_name="حداکثر تلاش کد تایید")
    otp_lock_minutes = models.PositiveIntegerField(default=15, verbose_name="مدت قفل پس از خطا (دقیقه)")

    back_in_stock_start_hour = models.PositiveSmallIntegerField(default=8, verbose_name="شروع ساعت ارسال «موجود شد»")
    back_in_stock_end_hour = models.PositiveSmallIntegerField(default=21, verbose_name="پایان ساعت ارسال «موجود شد»")

    trust_marks_html = models.TextField(
        blank=True,
        verbose_name="کد HTML نمادهای اعتماد",
        help_text="فقط کد HTML نماد اعتماد (مثلاً اینماد). خالی = نمایش داده نمی‌شود.",
    )

    # Legal seller details for printable order invoices (C7)
    legal_name = models.CharField(max_length=200, blank=True, verbose_name="نام حقوقی / فروشنده")
    economic_code = models.CharField(max_length=32, blank=True, verbose_name="کد اقتصادی")
    national_id = models.CharField(max_length=32, blank=True, verbose_name="شناسه ملی")
    registration_no = models.CharField(max_length=32, blank=True, verbose_name="شماره ثبت")
    legal_address = models.TextField(blank=True, verbose_name="آدرس حقوقی")
    legal_postal_code = models.CharField(max_length=16, blank=True, verbose_name="کدپستی فروشنده")
    legal_phone = models.CharField(max_length=40, blank=True, verbose_name="تلفن فاکتور")

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self) -> str:
        return self.store_name or "تنظیمات سایت"

    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        kwargs.pop("force_insert", None)
        if not self.created_at:
            existing_created_at = SiteSettings.objects.filter(pk=1).values_list("created_at", flat=True).first()
            if existing_created_at is not None:
                self.created_at = existing_created_at
        super().save(*args, **kwargs)
        transaction.on_commit(self._invalidate_cache)

    def delete(self, *args, **kwargs):
        res = super().delete(*args, **kwargs)
        transaction.on_commit(self._invalidate_cache)
        return res

    @staticmethod
    def _invalidate_cache() -> None:
        safe_cache_delete(SITE_SETTINGS_CACHE_KEY)
        safe_cache_incr_epoch()

    @classmethod
    def get_solo(cls) -> SiteSettings:
        cached = safe_cache_get(SITE_SETTINGS_CACHE_KEY)
        if isinstance(cached, cls):
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        safe_cache_set(SITE_SETTINGS_CACHE_KEY, obj)
        return obj


class StaticPage(TimeStampedModel):
    """Admin-managed informational pages (about, terms, returns, privacy, contact)."""

    slug = models.SlugField(max_length=120, unique=True, allow_unicode=True, verbose_name="نشانی (slug)")
    title = models.CharField(max_length=200, verbose_name="عنوان")
    body = models.TextField(blank=True, verbose_name="متن صفحه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    needs_review = models.BooleanField(
        default=False,
        verbose_name="نیازمند بازبینی",
        help_text="برای متن‌های پیش‌نویس روشن است؛ پس از تایید نهایی خاموش کنید.",
    )
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان سئو")
    seo_description = models.CharField(max_length=320, blank=True, verbose_name="توضیحات سئو")

    class Meta:
        verbose_name = "صفحه ثابت"
        verbose_name_plural = "صفحات ثابت"
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class FooterLink(TimeStampedModel):
    """Admin-managed links organized into footer columns."""

    GROUP_ABOUT = "about"
    GROUP_GUIDE = "guide"
    GROUP_SERVICE = "service"
    GROUP_CHOICES = [
        (GROUP_ABOUT, "درباره مل‌مل"),
        (GROUP_GUIDE, "راهنمای خرید"),
        (GROUP_SERVICE, "خدمات مشتریان"),
    ]

    group = models.CharField(max_length=32, choices=GROUP_CHOICES, verbose_name="ستون")
    title = models.CharField(max_length=120, verbose_name="عنوان لینک")
    url = models.CharField(max_length=300, verbose_name="آدرس")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "لینک فوتر"
        verbose_name_plural = "لینک‌های فوتر"
        ordering = ["group", "sort", "id"]

    def __str__(self) -> str:
        return f"{self.get_group_display()} — {self.title}"

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        transaction.on_commit(self._invalidate_cache)

    def delete(self, *args, **kwargs):
        res = super().delete(*args, **kwargs)
        transaction.on_commit(self._invalidate_cache)
        return res

    @staticmethod
    def _invalidate_cache() -> None:
        safe_cache_delete(FOOTER_LINKS_CACHE_KEY)
        safe_cache_incr_epoch()

    @classmethod
    def get_grouped(cls) -> list[dict]:
        cached = safe_cache_get(FOOTER_LINKS_CACHE_KEY)
        if cached is not None:
            return cached

        links = list(cls.objects.filter(is_active=True).order_by("group", "sort", "id"))
        by_group: dict[str, list[dict]] = {code: [] for code, _ in cls.GROUP_CHOICES}
        for link in links:
            if link.group in by_group:
                by_group[link.group].append({"title": link.title, "url": link.url})

        grouped = [
            {"code": code, "label": label, "links": by_group[code]}
            for code, label in cls.GROUP_CHOICES
            if by_group[code]
        ]
        safe_cache_set(FOOTER_LINKS_CACHE_KEY, grouped)
        return grouped
