"""Django admin for accounts (D19, D20)."""

from __future__ import annotations

from django.contrib import admin, messages

from apps.accounts import maintenance
from apps.accounts.models import Address, OTPChallenge, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("mobile", "full_name", "national_code", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("mobile", "first_name", "last_name", "email", "national_code")
    ordering = ("-date_joined", "-id")
    readonly_fields = ("last_login", "date_joined", "session_version")
    exclude = ("password",)
    fieldsets = (
        ("ورود", {"fields": ("mobile",)}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "national_code", "email")}),
        (
            "دسترسی",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("نشست و تاریخ‌ها", {"fields": ("session_version", "last_login", "date_joined")}),
    )
    filter_horizontal = ("groups", "user_permissions")

    def has_add_permission(self, request) -> bool:
        # Staff accounts are created via `manage.py createsuperuser` / shell.
        return False

    @admin.display(description="نام")
    def full_name(self, obj) -> str:
        return obj.get_full_name()

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.has_perm("accounts.change_national_code"):
            readonly.append("national_code")
        return readonly

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = User.objects.filter(pk=obj.pk).values_list("national_code", flat=True).first()
        can_change_national_code = request.user.has_perm("accounts.change_national_code")
        changed_national_code = change and previous and obj.national_code != previous

        if changed_national_code:
            if not can_change_national_code:
                messages.error(request, "برای تغییر کد ملی مجوز لازم را ندارید.")
                return
            obj.allow_national_code_change()
            super().save_model(request, obj, form, change)
            self.log_change(
                request,
                obj,
                f"National code changed from {previous} to {obj.national_code}.",
            )
            messages.info(request, "تغییر کد ملی ثبت شد.")
            return

        super().save_model(request, obj, form, change)


@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ("mobile", "created_at", "expires_at", "attempts", "locked_until", "consumed_at", "is_active")
    search_fields = ("mobile",)
    ordering = ("-created_at", "-id")
    actions = ("purge_stale",)
    readonly_fields = (
        "mobile",
        "code_hmac",
        "expires_at",
        "last_sent_at",
        "attempts",
        "max_attempts",
        "locked_until",
        "consumed_at",
        "ip",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_purge_permission(self, request) -> bool:
        return request.user.is_superuser

    @admin.action(description="پاک‌سازی چالش‌های منقضی‌شده‌ی قدیمی‌تر از ۱ روز", permissions=["purge"])
    def purge_stale(self, request, queryset):
        deleted = maintenance.purge_otp_challenges(queryset=queryset)
        self.message_user(request, f"{deleted} چالش پاک شد", messages.SUCCESS)

    @admin.display(description="فعال")
    def is_active(self, obj) -> bool:
        return obj.is_active


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "user", "province", "city", "is_default", "deleted_at")
    list_filter = ("province", "is_default")
    search_fields = ("recipient_name", "recipient_mobile", "address_text", "user__mobile")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    fieldsets = (
        ("مالک", {"fields": ("user", "title", "is_default")}),
        ("گیرنده", {"fields": ("recipient_name", "recipient_mobile")}),
        ("نشانی", {"fields": ("province", "city", "address_text", "plate", "unit", "postal_code")}),
        ("موقعیت", {"fields": ("lat", "lng")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at", "deleted_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "province", "city")

    def save_model(self, request, obj, form, change):
        if obj.deleted_at is not None:
            obj.is_default = False
        if obj.is_default:
            Address.objects.filter(
                user=obj.user,
                is_default=True,
                deleted_at__isnull=True,
            ).exclude(pk=obj.pk).update(is_default=False)
        super().save_model(request, obj, form, change)
