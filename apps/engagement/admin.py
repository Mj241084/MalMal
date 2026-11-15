"""Admin: moderation queue for reviews, read-only likes and daily stats."""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone

from apps.engagement import services
from apps.engagement.models import Like, ProductDailyStat, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "status", "is_verified_buyer", "has_reply", "created_at")
    list_filter = ("status", "rating", "is_verified_buyer")
    search_fields = ("product__title", "user__mobile", "body")
    list_select_related = ("product", "user")
    ordering = ("-created_at",)
    actions = ("approve_selected", "reject_selected")
    fields = (
        "product",
        "user",
        "rating",
        "body",
        "is_verified_buyer",
        "status",
        "rejection_reason",
        "admin_reply",
        "moderated_by",
        "moderated_at",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "product",
        "user",
        "rating",
        "body",
        "is_verified_buyer",
        "moderated_by",
        "moderated_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    @admin.display(description="پاسخ", boolean=True)
    def has_reply(self, obj) -> bool:
        return bool(obj.admin_reply)

    def save_model(self, request, obj, form, change):
        if "status" in form.changed_data:
            obj.moderated_by = request.user
            obj.moderated_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="تایید نظرهای انتخاب‌شده")
    def approve_selected(self, request, queryset):
        reviews = list(queryset)
        for review in reviews:
            services.moderate(review, Review.APPROVED, by=request.user)
        self.message_user(request, f"{len(reviews)} نظر تایید شد.", messages.SUCCESS)

    @admin.action(description="رد نظرهای انتخاب‌شده (دلیل را در صفحه‌ی هر نظر بنویسید)")
    def reject_selected(self, request, queryset):
        reviews = list(queryset)
        for review in reviews:
            services.moderate(review, Review.REJECTED, by=request.user)
        self.message_user(request, f"{len(reviews)} نظر رد شد.", messages.SUCCESS)


class _ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(Like)
class LikeAdmin(_ReadOnlyAdmin):
    list_display = ("product", "user", "created_at")
    search_fields = ("product__title", "user__mobile")
    list_select_related = ("product", "user")
    ordering = ("-created_at",)


@admin.register(ProductDailyStat)
class ProductDailyStatAdmin(_ReadOnlyAdmin):
    list_display = ("product", "date", "purchases")
    list_filter = ("date",)
    ordering = ("-date",)
