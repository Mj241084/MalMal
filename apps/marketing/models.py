"""Marketing models: trust claims, banners, collections and home page blocks (docs/03 §3)."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.catalog.filters import SORT_CHOICES as CATALOG_SORT_CHOICES
from apps.catalog.utils import unique_slug
from apps.core.models import TimeStampedModel

MAX_IMAGE_BYTES = 1024 * 1024
SORT_CHOICES = [*CATALOG_SORT_CHOICES, ("discount", "بیشترین تخفیف")]


def validate_image_size(file) -> None:
    # Only fresh uploads: re-validating an unchanged file would hit the storage on every save.
    if file and not getattr(file, "_committed", True) and file.size > MAX_IMAGE_BYTES:
        raise ValidationError("حجم تصویر نباید بیشتر از ۱ مگابایت باشد.")


IMAGE_VALIDATORS = [FileExtensionValidator(["webp", "jpg", "jpeg", "png"]), validate_image_size]


def in_window(now, starts_at, ends_at) -> bool:
    return (starts_at is None or starts_at <= now) and (ends_at is None or now < ends_at)


def is_safe_target(url: str) -> bool:
    if url.startswith("https://"):
        return True
    return url.startswith("/") and url_has_allowed_host_and_scheme(url, allowed_hosts=None)


class TrustItem(TimeStampedModel):
    """A promise the store makes («ارسال به سراسر کشور»، «ضمانت اصالت» …), shown on the home and product pages."""

    icon = models.CharField(
        max_length=64,
        verbose_name="نام آیکون",
        help_text="نام نماد در sprite (مثلاً truck، shield-check، lock، phone).",
    )
    title = models.CharField(max_length=120, verbose_name="عنوان")
    subtitle = models.CharField(max_length=200, blank=True, verbose_name="توضیح کوتاه")
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


class ScheduledModel(TimeStampedModel):
    """Shared start/end window for banners and collections (docs/02 §8.1)."""

    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="شروع نمایش")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="پایان نمایش")

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "پایان نمایش باید بعد از شروع باشد."})

    def is_live(self, now=None) -> bool:
        return self.is_active and in_window(now or timezone.now(), self.starts_at, self.ends_at)


class Banner(ScheduledModel):
    PLACEMENT_HERO = "home_hero"
    PLACEMENT_STRIP = "home_strip"
    PLACEMENT_CHOICES = [(PLACEMENT_HERO, "اسلایدر صفحه‌ی اصلی"), (PLACEMENT_STRIP, "نوار باریک صفحه‌ی اصلی")]

    TARGET_NONE = "none"
    TARGET_PRODUCT = "product"
    TARGET_CATEGORY = "category"
    TARGET_COLLECTION = "collection"
    TARGET_URL = "url"
    TARGET_CHOICES = [
        (TARGET_NONE, "بدون لینک"),
        (TARGET_PRODUCT, "محصول"),
        (TARGET_CATEGORY, "دسته"),
        (TARGET_COLLECTION, "مجموعه"),
        (TARGET_URL, "نشانی دلخواه"),
    ]
    TARGET_ATTRS = {
        TARGET_PRODUCT: "target_product_id",
        TARGET_CATEGORY: "target_category_id",
        TARGET_COLLECTION: "target_collection_id",
        TARGET_URL: "target_url",
    }

    title = models.CharField(max_length=120, verbose_name="عنوان (داخلی)")
    alt = models.CharField(max_length=200, verbose_name="متن جایگزین تصویر")
    image_desktop = models.ImageField(
        upload_to="banners/",
        validators=IMAGE_VALIDATORS,
        verbose_name="تصویر دسکتاپ",
        help_text="اسلایدر ۱۴۴۰×۴۸۰ (۳:۱)، نوار باریک ۱۴۴۰×۱۸۰ (۸:۱). حداکثر ۱ مگابایت؛ WebP، JPG یا PNG.",
    )
    image_mobile = models.ImageField(
        upload_to="banners/",
        blank=True,
        validators=IMAGE_VALIDATORS,
        verbose_name="تصویر موبایل",
        help_text="اسلایدر ۸۰۰×۶۰۰ (۴:۳)، نوار باریک ۸۰۰×۲۶۷ (۳:۱). خالی = همان تصویر دسکتاپ.",
    )
    placement = models.CharField(
        max_length=16, choices=PLACEMENT_CHOICES, default=PLACEMENT_HERO, verbose_name="جایگاه"
    )
    target_type = models.CharField(max_length=12, choices=TARGET_CHOICES, default=TARGET_NONE, verbose_name="نوع مقصد")
    target_product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="محصول"
    )
    target_category = models.ForeignKey(
        "catalog.Category", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="دسته"
    )
    target_collection = models.ForeignKey(
        "marketing.Collection",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="مجموعه",
    )
    target_url = models.CharField(
        max_length=300, blank=True, verbose_name="نشانی دلخواه", help_text="مسیر داخلی (/…) یا نشانی https."
    )
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "بنر"
        verbose_name_plural = "بنرها"
        ordering = ["placement", "sort", "pk"]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        super().clean()
        errors = {}
        for kind, attr in self.TARGET_ATTRS.items():
            field = attr.removesuffix("_id")
            if kind == self.target_type and not getattr(self, attr):
                errors[field] = "برای این نوع مقصد، این فیلد را پر کنید."
            elif kind != self.target_type and getattr(self, attr):
                errors[field] = "با نوع مقصد انتخاب‌شده سازگار نیست."
        if self.target_type == self.TARGET_URL and self.target_url and not is_safe_target(self.target_url):
            errors["target_url"] = "فقط مسیر داخلی (با /) یا نشانی https مجاز است."
        if errors:
            raise ValidationError(errors)


class CollectionQuerySet(models.QuerySet):
    def live(self, now=None):
        now = now or timezone.now()
        return (
            self.filter(is_active=True)
            .filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now))
            .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))
        )


class Collection(ScheduledModel):
    MODE_MANUAL = "manual"
    MODE_RULE = "rule"
    MODE_CHOICES = [(MODE_MANUAL, "دستی (انتخاب محصولات)"), (MODE_RULE, "قاعده‌ای")]

    title = models.CharField(max_length=160, verbose_name="عنوان")
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True, verbose_name="نشانی")
    description = models.TextField(blank=True, verbose_name="توضیح")
    cover = models.ImageField(
        upload_to="collections/",
        blank=True,
        validators=IMAGE_VALIDATORS,
        verbose_name="کاور",
        help_text="۱۲۰۰×۸۰۰ (۳:۲). برای فهرست مجموعه‌ها و اشتراک‌گذاری.",
    )
    mode = models.CharField(max_length=8, choices=MODE_CHOICES, default=MODE_MANUAL, verbose_name="حالت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    # rule mode only
    categories = models.ManyToManyField(
        "catalog.Category", blank=True, related_name="collections", verbose_name="دسته‌ها"
    )
    brands = models.ManyToManyField("catalog.Brand", blank=True, related_name="collections", verbose_name="برندها")
    min_discount_pct = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(99)], verbose_name="حداقل درصد تخفیف"
    )
    min_price = models.BigIntegerField(null=True, blank=True, verbose_name="حداقل قیمت (تومان)")
    max_price = models.BigIntegerField(null=True, blank=True, verbose_name="حداکثر قیمت (تومان)")
    only_in_stock = models.BooleanField(default=False, verbose_name="فقط موجود")
    sort_by = models.CharField(max_length=16, choices=SORT_CHOICES, default="newest", verbose_name="مرتب‌سازی پیش‌فرض")
    seo_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان سئو")
    seo_description = models.CharField(max_length=320, blank=True, verbose_name="توضیحات سئو")

    objects = CollectionQuerySet.as_manager()

    class Meta:
        verbose_name = "مجموعه"
        verbose_name_plural = "مجموعه‌ها"
        ordering = ["-pk"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("marketing:collection", args=[self.slug])

    def clean(self) -> None:
        super().clean()
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValidationError({"max_price": "حداکثر قیمت نباید کمتر از حداقل باشد."})

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)


class CollectionItem(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="+", verbose_name="محصول")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "محصول مجموعه"
        verbose_name_plural = "محصولات مجموعه"
        ordering = ["sort", "pk"]
        constraints = [models.UniqueConstraint(fields=["collection", "product"], name="uniq_collection_product")]


class HomeBlock(TimeStampedModel):
    HERO = "hero"
    CATEGORIES = "categories"
    PRODUCT_RAIL = "product_rail"
    COLLECTION_RAIL = "collection_rail"
    BANNER_STRIP = "banner_strip"
    BRANDS = "brands"
    TRUST = "trust"
    KIND_CHOICES = [
        (HERO, "اسلایدر بنر"),
        (CATEGORIES, "دسته‌های برتر"),
        (PRODUCT_RAIL, "ردیف محصولات"),
        (COLLECTION_RAIL, "ردیف مجموعه"),
        (BANNER_STRIP, "نوار باریک بنر"),
        (BRANDS, "برندها"),
        (TRUST, "مزیت‌های فروشگاه"),
    ]
    SOURCE_BEST = "best_selling"
    SOURCE_NEWEST = "newest"
    SOURCE_DISCOUNTED = "discounted"
    SOURCE_CHOICES = [(SOURCE_BEST, "پرفروش‌ترین‌ها"), (SOURCE_NEWEST, "جدیدترین‌ها"), (SOURCE_DISCOUNTED, "تخفیف‌دارها")]

    kind = models.CharField(max_length=16, choices=KIND_CHOICES, verbose_name="نوع بلوک")
    title = models.CharField(max_length=120, blank=True, verbose_name="عنوان", help_text="خالی = عنوان پیش‌فرض.")
    rail_source = models.CharField(
        max_length=16,
        choices=SOURCE_CHOICES,
        blank=True,
        verbose_name="منبع ردیف",
        help_text="فقط برای «ردیف محصولات».",
    )
    category = models.ForeignKey(
        "catalog.Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="محدود به دسته",
        help_text="فقط برای «ردیف محصولات». خالی = همه‌ی دسته‌ها.",
    )
    collection = models.ForeignKey(
        Collection,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="مجموعه",
        help_text="فقط برای «ردیف مجموعه».",
    )
    limit = models.PositiveSmallIntegerField(
        default=12,
        validators=[MaxValueValidator(24)],
        verbose_name="تعداد",
        help_text="تعداد آیتم ردیف، دسته یا برند. برای اسلایدر و نوار بی‌اثر است.",
    )
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "بلوک صفحه‌ی اصلی"
        verbose_name_plural = "بلوک‌های صفحه‌ی اصلی"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.title or self.get_kind_display()

    def clean(self) -> None:
        super().clean()
        errors = {}
        if self.kind == self.COLLECTION_RAIL and not self.collection_id:
            errors["collection"] = "برای این نوع، مجموعه را انتخاب کنید."
        if self.kind == self.PRODUCT_RAIL and not self.rail_source:
            errors["rail_source"] = "برای این نوع، منبع ردیف را انتخاب کنید."
        if self.kind in (self.HERO, self.BANNER_STRIP) and (
            HomeBlock.objects.filter(kind=self.kind).exclude(pk=self.pk).exists()
        ):
            errors["kind"] = "از این نوع فقط یک بلوک می‌تواند وجود داشته باشد."
        if errors:
            raise ValidationError(errors)
