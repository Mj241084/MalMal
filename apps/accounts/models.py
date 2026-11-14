"""Account models: custom user, OTP challenges, addresses (docs/03 §3)."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.core.text import normalize_fa
from apps.core.validators import normalize_iran_mobile, normalize_national_code, validate_national_code

NATIONAL_CODE_LOCKED_MESSAGE = "کد ملی بعد از ثبت قابل تغییر نیست."

_mobile_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره‌ی موبایل باید با ۰۹ شروع شود و ۱۱ رقم باشد.",
)


class UserManager(BaseUserManager):
    """Create users keyed by normalized Iranian mobile numbers."""

    use_in_migrations = True

    def _create_user(self, mobile: str, password: str | None, **extra):
        if not mobile:
            raise ValueError("Mobile number is required.")
        user = self.model(mobile=normalize_iran_mobile(mobile), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, mobile: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(mobile, password, **extra)

    def create_superuser(self, mobile: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if not password:
            raise ValueError("Superuser must have a password.")
        return self._create_user(mobile, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    mobile = models.CharField(
        max_length=11,
        unique=True,
        validators=[_mobile_validator],
        verbose_name="موبایل",
    )
    first_name = models.CharField(max_length=80, blank=True, verbose_name="نام")
    last_name = models.CharField(max_length=80, blank=True, verbose_name="نام خانوادگی")
    national_code = models.CharField(
        max_length=10,
        blank=True,
        validators=[validate_national_code],
        verbose_name="کد ملی",
    )
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    session_version = models.PositiveIntegerField(default=0, verbose_name="نسخه‌ی نشست")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    is_staff = models.BooleanField(default=False, verbose_name="دسترسی ادمین")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="تاریخ عضویت")

    objects = UserManager()

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["-date_joined", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=~Q(email=""),
                name="unique_user_email_when_set",
                violation_error_message="این ایمیل قبلاً برای حساب دیگری ثبت شده است",
            ),
        ]
        permissions = [
            ("change_national_code", "Can change a customer's national code"),
        ]

    def __str__(self) -> str:
        full_name = self.get_full_name()
        return f"{full_name} ({self.mobile})" if full_name else self.mobile

    def get_full_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()

    def get_short_name(self) -> str:
        return self.first_name or self.mobile

    def get_session_auth_hash(self) -> str:
        """Include `session_version` and `is_active` so bumping/deactivating revokes sessions."""
        key = f"{self.pk}:{self.session_version}:{int(self.is_active)}:{self.password}"
        return salted_hmac("accounts.User.session_auth", key).hexdigest()

    def clean(self) -> None:
        super().clean()
        if self.mobile:
            self.mobile = normalize_iran_mobile(self.mobile)
        if self.first_name:
            self.first_name = normalize_fa(self.first_name)
        if self.last_name:
            self.last_name = normalize_fa(self.last_name)
        if self.national_code:
            self.national_code = normalize_national_code(self.national_code)
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, **kwargs):
        self._enforce_national_code_lock()
        if self.mobile:
            self.mobile = normalize_iran_mobile(self.mobile)
        if self.national_code:
            self.national_code = normalize_national_code(self.national_code)
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def _enforce_national_code_lock(self) -> None:
        """D20: once a national code is set, only a permitted admin flow may change it."""
        if not self.pk:
            return
        previous = type(self).objects.filter(pk=self.pk).values_list("national_code", flat=True).first()
        if previous and self.national_code != previous and not self._national_code_change_allowed:
            raise ValidationError({"national_code": NATIONAL_CODE_LOCKED_MESSAGE})

    _national_code_change_allowed = False

    def allow_national_code_change(self) -> None:
        """Open the D20 lock for this instance; callers must verify permission and log the change."""
        self._national_code_change_allowed = True


class OTPChallenge(models.Model):
    """One active challenge per mobile. The code itself is never stored, only its HMAC."""

    mobile = models.CharField(
        max_length=11,
        unique=True,
        validators=[_mobile_validator],
        verbose_name="موبایل",
    )
    code_hmac = models.CharField(max_length=64, verbose_name="هش کد")
    expires_at = models.DateTimeField(verbose_name="انقضا")
    last_sent_at = models.DateTimeField(default=timezone.now, verbose_name="آخرین ارسال")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="تلاش‌ها")
    max_attempts = models.PositiveSmallIntegerField(default=5, verbose_name="حداکثر تلاش")
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name="قفل تا")
    consumed_at = models.DateTimeField(null=True, blank=True, verbose_name="مصرف در")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="ساخت")

    class Meta:
        verbose_name = "چالش کد یک‌بارمصرف"
        verbose_name_plural = "چالش‌های کد یک‌بارمصرف"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.mobile} ({self.expires_at:%Y-%m-%d %H:%M})"

    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > timezone.now()

    @property
    def is_active(self) -> bool:
        """docs/03: consumed_at IS NULL AND expires_at > now AND not locked and attempts < max."""
        return (
            self.consumed_at is None
            and self.expires_at > timezone.now()
            and not self.is_locked
            and self.attempts < self.max_attempts
        )

    @property
    def seconds_remaining(self) -> int:
        if self.consumed_at is not None:
            return 0
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    @property
    def lock_seconds_remaining(self) -> int:
        if self.locked_until is None:
            return 0
        return max(0, int((self.locked_until - timezone.now()).total_seconds()))


class Address(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name="کاربر",
    )
    title = models.CharField(max_length=60, blank=True, verbose_name="عنوان")
    recipient_name = models.CharField(max_length=120, verbose_name="نام گیرنده")
    recipient_mobile = models.CharField(
        max_length=11,
        validators=[_mobile_validator],
        verbose_name="موبایل گیرنده",
    )
    province = models.ForeignKey(
        "geo.Province",
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name="استان",
    )
    city = models.ForeignKey(
        "geo.City",
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name="شهر",
    )
    address_text = models.TextField(verbose_name="آدرس کامل")
    plate = models.CharField(max_length=20, verbose_name="پلاک")
    unit = models.CharField(max_length=20, blank=True, verbose_name="واحد")
    postal_code = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r"^\d{10}$", message="کدپستی باید دقیقاً ۱۰ رقم باشد.")],
        verbose_name="کدپستی",
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="عرض جغرافیایی")
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="طول جغرافیایی")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="حذف‌شده در")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="ساخت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="ویرایش")

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"
        ordering = ["-is_default", "id"]
        indexes = [
            models.Index(fields=["user", "deleted_at"], name="address_user_deleted_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True, deleted_at__isnull=True),
                name="unique_default_address_per_user",
            ),
        ]

    def __str__(self) -> str:
        return self.title or f"{self.province}، {self.city}"

    def _normalize_fields(self) -> None:
        if self.title:
            self.title = normalize_fa(self.title)
        if self.recipient_name:
            self.recipient_name = normalize_fa(self.recipient_name)
        if self.recipient_mobile:
            self.recipient_mobile = normalize_iran_mobile(self.recipient_mobile)
        if self.address_text:
            self.address_text = normalize_fa(self.address_text)
        if self.plate:
            self.plate = normalize_fa(self.plate)
        if self.unit:
            self.unit = normalize_fa(self.unit)
        if self.postal_code:
            self.postal_code = normalize_fa(self.postal_code).strip()

    def clean(self) -> None:
        super().clean()
        self._normalize_fields()
        if self.city_id and self.province_id and self.city.province_id != self.province_id:
            raise ValidationError({"city": "شهر انتخاب‌شده متعلق به این استان نیست"})
        if (self.lat is None) != (self.lng is None):
            raise ValidationError("مختصات نقشه ناقص است")

    def save(self, *args, **kwargs):
        self._normalize_fields()
        super().save(*args, **kwargs)
