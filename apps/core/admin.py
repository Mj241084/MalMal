"""Django admin configuration for core models."""

from __future__ import annotations

from django.contrib import admin

from apps.core.models import FooterLink, SiteSettings, StaticPage


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("store_name", "phone", "low_stock_threshold", "updated_at")
    fieldsets = (
        (
            "اطلاعات فروشگاه",
            {
                "fields": (
                    "store_name",
                    "phone",
                    "email",
                    "address",
                    "working_hours",
                )
            },
        ),
        (
            "شبکه‌های اجتماعی",
            {
                "fields": (
                    "instagram_url",
                    "telegram_url",
                    "x_url",
                    "bale_url",
                    "eitaa_url",
                    "rubika_url",
                    "igap_url",
                    "soroush_url",
                    "whatsapp_url",
                )
            },
        ),
        ("لوگو", {"fields": ("logo_light", "logo_dark")}),
        (
            "تنظیمات فروش و پیامک",
            {
                "fields": (
                    "free_shipping_threshold",
                    "low_stock_threshold",
                    "otp_ttl_seconds",
                    "otp_max_attempts",
                    "otp_lock_minutes",
                    "back_in_stock_start_hour",
                    "back_in_stock_end_hour",
                )
            },
        ),
        ("نمادهای اعتماد", {"fields": ("trust_marks_html",)}),
        (
            "مشخصات حقوقی فروشنده (فاکتور)",
            {
                "fields": (
                    "legal_name",
                    "economic_code",
                    "national_id",
                    "registration_no",
                    "legal_address",
                    "legal_postal_code",
                    "legal_phone",
                )
            },
        ),
    )

    def has_add_permission(self, request) -> bool:
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_active", "needs_review", "updated_at")
    list_filter = ("is_active", "needs_review")
    search_fields = ("title", "slug", "body")
    ordering = ("title",)


@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "group", "url", "sort", "is_active")
    list_filter = ("group", "is_active")
    search_fields = ("title", "url")
    ordering = ("group", "sort", "id")
