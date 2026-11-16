"""Order, order item, status log and shipping method models (docs/03 §3)."""

from __future__ import annotations

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ShippingMethod(TimeStampedModel):
    PAYMENT_PREPAID = "prepaid"
    PAYMENT_COLLECT = "collect"
    PAYMENT_CHOICES = [(PAYMENT_PREPAID, "کرایه در سایت"), (PAYMENT_COLLECT, "پس‌کرایه")]

    code = models.SlugField(max_length=32, unique=True, verbose_name="کد")
    title = models.CharField(max_length=120, verbose_name="عنوان")
    product_note = models.CharField(max_length=200, blank=True, verbose_name="متن صفحه‌ی محصول")
    checkout_note = models.CharField(max_length=300, blank=True, verbose_name="متن checkout")
    has_tracking = models.BooleanField(default=True, verbose_name="با کد رهگیری؟")
    payment_mode = models.CharField(
        max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_COLLECT, verbose_name="نحوه‌ی پرداخت کرایه"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        verbose_name = "روش ارسال"
        verbose_name_plural = "روش‌های ارسال"
        ordering = ["sort", "pk"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        transaction.on_commit(_bump_detail_pages)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        transaction.on_commit(_bump_detail_pages)
        return result


def _bump_detail_pages() -> None:
    # The product page embeds the shipping text, and it is cached under the site-wide trust revision.
    from apps.marketing.cache import bump_trust_revision

    bump_trust_revision()


STATUS_DOT = {  # docs/04 §9.4
    "pending_payment": "status-warning",
    "paid": "status-info",
    "processing": "status-info",
    "shipped": "status-info",
    "delivered": "status-success",
    "cancelled": "status-error",
    "expired": "status-neutral",
    "refunded": "status-neutral",
}


class Order(TimeStampedModel):
    PENDING = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    STATUS_CHOICES = [
        (PENDING, "در انتظار پرداخت"),
        (PAID, "پرداخت‌شده"),
        (PROCESSING, "در حال آماده‌سازی"),
        (SHIPPED, "ارسال‌شده"),
        (DELIVERED, "تحویل‌شده"),
        (CANCELLED, "لغوشده"),
        (EXPIRED, "منقضی‌شده"),
        (REFUNDED, "بازگشت وجه"),
    ]

    number = models.CharField(max_length=16, unique=True, verbose_name="شماره سفارش")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders", verbose_name="کاربر"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, verbose_name="وضعیت")

    items_total = models.BigIntegerField(verbose_name="جمع کالاها (تومان)")
    shipping_cost = models.BigIntegerField(default=0, verbose_name="هزینه‌ی ارسال (تومان)")
    payable = models.BigIntegerField(verbose_name="مبلغ قابل پرداخت (تومان)")

    buyer_name = models.CharField(max_length=170, verbose_name="نام خریدار")
    buyer_mobile = models.CharField(max_length=11, verbose_name="موبایل خریدار")
    buyer_national_code = models.CharField(max_length=10, verbose_name="کد ملی خریدار")
    buyer_email = models.EmailField(blank=True, verbose_name="ایمیل خریدار")

    recipient_name = models.CharField(max_length=120, verbose_name="نام گیرنده")
    recipient_mobile = models.CharField(max_length=11, verbose_name="موبایل گیرنده")
    province_name = models.CharField(max_length=80, verbose_name="استان")
    city_name = models.CharField(max_length=100, verbose_name="شهر")
    address_text = models.TextField(verbose_name="آدرس")
    plate = models.CharField(max_length=20, verbose_name="پلاک")
    unit = models.CharField(max_length=20, blank=True, verbose_name="واحد")
    postal_code = models.CharField(max_length=10, verbose_name="کدپستی")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    shipping_method = models.ForeignKey(
        ShippingMethod, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    shipping_method_title = models.CharField(max_length=120, verbose_name="روش ارسال")
    shipping_payment_mode = models.CharField(max_length=10, verbose_name="نحوه‌ی پرداخت کرایه")
    tracking_code = models.CharField(max_length=64, blank=True, verbose_name="کد رهگیری")

    reserved_until = models.DateTimeField(null=True, blank=True, verbose_name="رزرو تا")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پرداخت")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at", "-id"]
        permissions = [("manage_order_status", "Can change an order's status")]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="order_user_created_idx"),
            models.Index(fields=["status", "reserved_until"], name="order_status_reserved_idx"),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def status_dot(self) -> str:
        return STATUS_DOT[self.status]

    @property
    def can_pay_now(self) -> bool:
        return self.status == self.PENDING and self.reserved_until is not None and self.reserved_until > timezone.now()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", null=True, on_delete=models.SET_NULL, related_name="+")
    variant = models.ForeignKey("catalog.Variant", null=True, on_delete=models.SET_NULL, related_name="+")
    product_title = models.CharField(max_length=255)
    variant_title = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    unit_price = models.BigIntegerField()
    qty = models.PositiveSmallIntegerField()
    image_path = models.CharField(max_length=300, blank=True)
    warranty_text = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.product_title} × {self.qty}"

    @property
    def line_total(self) -> int:
        return self.unit_price * self.qty

    @property
    def image_url(self) -> str:
        return f"{settings.MEDIA_URL}{self.image_path}" if self.image_path else ""


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت سفارش"
        verbose_name_plural = "تاریخچه‌ی وضعیت سفارش‌ها"
        ordering = ["created_at", "id"]


# The states in which the invoice exists and the money was actually taken (docs/02 §7).
PAID_STATES = (Order.PAID, Order.PROCESSING, Order.SHIPPED, Order.DELIVERED)
