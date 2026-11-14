"""Admin for site-wide trust items."""

from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from apps.marketing.models import TrustItem


@admin.register(TrustItem)
class TrustItemAdmin(admin.ModelAdmin):
    list_display = ("title", "icon_preview", "subtitle", "is_placeholder", "sort", "is_active")
    list_filter = ("is_active", "is_placeholder")
    list_editable = ("sort", "is_active")
    search_fields = ("title", "subtitle")
    ordering = ("sort", "pk")

    @admin.display(description="آیکون")
    def icon_preview(self, obj) -> str:
        return format_html("<code>{}</code>", obj.icon)
