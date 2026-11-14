"""Django admin for SMS logs."""

from __future__ import annotations

from django.contrib import admin, messages

from apps.notifications import maintenance
from apps.notifications.models import SmsLog


@admin.register(SmsLog)
class SmsLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "mobile", "status", "provider_message_id")
    list_filter = ("status", "kind")
    search_fields = ("mobile", "provider_message_id")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    actions = ("purge_stale",)
    readonly_fields = (
        "mobile",
        "kind",
        "provider_message_id",
        "status",
        "error",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_purge_permission(self, request) -> bool:
        return request.user.is_superuser

    @admin.action(description="پاک‌سازی لاگ‌های قدیمی‌تر از ۹۰ روز", permissions=["purge"])
    def purge_stale(self, request, queryset):
        deleted = maintenance.purge_sms_logs(queryset=queryset)
        self.message_user(request, f"{deleted} لاگ پاک شد", messages.SUCCESS)
