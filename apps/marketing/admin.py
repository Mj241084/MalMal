"""Admin for trust items, banners, collections and home page blocks."""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils.html import format_html

from apps.core.jalali import jalali_str
from apps.marketing.forms import BannerAdminForm, CollectionAdminForm
from apps.marketing.models import Banner, Collection, CollectionItem, HomeBlock, TrustItem


@admin.register(TrustItem)
class TrustItemAdmin(admin.ModelAdmin):
    list_display = ("title", "icon_preview", "subtitle", "placeholder_notice", "sort", "is_active")
    list_filter = ("is_active", "is_placeholder")
    list_editable = ("sort", "is_active")
    search_fields = ("title", "subtitle")
    ordering = ("sort", "pk")

    @admin.display(description="آیکون")
    def icon_preview(self, obj) -> str:
        return format_html("<code>{}</code>", obj.icon)

    @admin.display(description="وضعیت")
    def placeholder_notice(self, obj):
        return format_html('<strong style="color:#b45309">{}</strong>', "متن فرضی") if obj.is_placeholder else "—"

    def changelist_view(self, request, extra_context=None):
        if TrustItem.objects.filter(is_active=True, is_placeholder=True).exists():
            messages.warning(
                request,
                "برخی مزیت‌های فعال هنوز متن فرضی دارند. قبل از انتشار آن‌ها را ویرایش و «متن فرضی» را خاموش کنید.",
            )
        return super().changelist_view(request, extra_context)


def _schedule(obj) -> str:
    return f"{jalali_str(obj.starts_at, '%Y/%m/%d') or '—'} تا {jalali_str(obj.ends_at, '%Y/%m/%d') or '—'}"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    form = BannerAdminForm
    list_display = ("title", "placement", "target_type", "schedule", "live", "sort", "is_active", "is_demo")
    list_editable = ("sort", "is_active")
    list_filter = ("placement", "is_active", "target_type", "is_demo")
    search_fields = ("title", "alt")
    autocomplete_fields = ("target_product", "target_category", "target_collection")
    readonly_fields = ("preview",)
    fieldsets = (
        (None, {"fields": ("title", "placement", "is_active", "sort")}),
        ("تصویر", {"fields": ("image_desktop", "image_mobile", "alt", "preview")}),
        ("مقصد", {"fields": ("target_type", "target_product", "target_category", "target_collection", "target_url")}),
        ("زمان‌بندی (تاریخ شمسی)", {"fields": ("starts_at", "ends_at")}),
        ("سایر", {"fields": ("is_demo",), "classes": ("collapse",)}),
    )

    @admin.display(description="زمان‌بندی")
    def schedule(self, obj) -> str:
        return _schedule(obj)

    @admin.display(description="در حال نمایش", boolean=True)
    def live(self, obj) -> bool:
        return obj.is_live()

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if not obj.pk or not obj.image_desktop:
            return "—"
        return format_html('<img src="{}" alt="" style="max-width:360px;border-radius:8px">', obj.image_desktop.url)


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0
    fields = ("product", "sort")
    autocomplete_fields = ("product",)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    form = CollectionAdminForm
    list_display = ("title", "mode", "schedule", "live", "is_active", "is_demo")
    list_filter = ("mode", "is_active", "is_demo")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("categories", "brands")
    inlines = (CollectionItemInline,)
    fieldsets = (
        (None, {"fields": ("title", "slug", "description", "cover", "mode", "is_active")}),
        ("زمان‌بندی (تاریخ شمسی)", {"fields": ("starts_at", "ends_at")}),
        (
            "قاعده (فقط حالت قاعده‌ای؛ بدون هیچ قاعده، همه‌ی محصولات می‌آیند)",
            {
                "fields": (
                    "categories",
                    "brands",
                    "min_discount_pct",
                    "min_price",
                    "max_price",
                    "only_in_stock",
                    "sort_by",
                )
            },
        ),
        ("سئو", {"fields": ("seo_title", "seo_description"), "classes": ("collapse",)}),
        ("سایر", {"fields": ("is_demo",), "classes": ("collapse",)}),
    )

    @admin.display(description="زمان‌بندی")
    def schedule(self, obj) -> str:
        return _schedule(obj)

    @admin.display(description="در حال نمایش", boolean=True)
    def live(self, obj) -> bool:
        return obj.is_live()


@admin.register(HomeBlock)
class HomeBlockAdmin(admin.ModelAdmin):
    list_display = ("sort", "kind", "title", "rail_source", "category", "collection", "limit", "is_active")
    list_display_links = ("kind",)
    list_editable = ("sort", "limit", "is_active")
    list_filter = ("kind", "is_active")
    list_select_related = ("category", "collection")
    ordering = ("sort", "pk")
