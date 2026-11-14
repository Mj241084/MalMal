"""Django admin for the catalog (docs/03 §9, docs/02 §12)."""

from __future__ import annotations

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils.html import format_html

from apps.catalog.models import (
    Brand,
    Category,
    Product,
    ProductImage,
    ProductSpecValue,
    SpecAttribute,
    StockMovement,
    Variant,
)
from apps.catalog.tree import subtree_upper_bound


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name_fa", "name_en", "slug", "product_count", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name_fa", "name_en", "aliases", "slug")
    ordering = ("name_fa",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count("products"))

    @admin.display(description="تعداد محصول", ordering="_product_count")
    def product_count(self, obj) -> int:
        return obj._product_count


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "path", "depth", "is_active", "is_featured", "show_in_menu", "menu_order")
    list_filter = ("is_active", "is_featured", "show_in_menu", "depth")
    search_fields = ("name", "slug", "path")
    ordering = ("path",)
    readonly_fields = ("path", "depth", "rev", "subtree_rev", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("parent", "name", "slug", "logo", "description")}),
        ("درخت", {"fields": ("path", "depth"), "classes": ("collapse",)}),
        ("منو", {"fields": ("is_featured", "featured_order", "show_in_menu", "menu_order")}),
        ("سایر", {"fields": ("is_active", "spec_inherit", "rev", "subtree_rev", "is_demo")}),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent" and request.resolver_match.kwargs.get("object_id"):
            current = Category.objects.filter(pk=request.resolver_match.kwargs["object_id"]).first()
            if current and current.path:
                blocked = Category.objects.filter(
                    path__gte=current.path, path__lt=subtree_upper_bound(current.path)
                ).values_list("pk", flat=True)
                kwargs["queryset"] = Category.objects.exclude(pk__in=list(blocked))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.parent_id and obj.pk and obj.parent.path.startswith(obj.path or "\0"):
            raise ValidationError("دسته نمی‌تواند زیرمجموعه‌ی خودش باشد.")
        super().save_model(request, obj, form, change)


class VariantInline(admin.StackedInline):
    model = Variant
    extra = 0
    fields = (
        "title",
        "sku",
        "options",
        "price",
        "compare_at_price",
        "stock",
        "max_per_order",
        "weight_g",
        "is_active",
        "sort",
    )
    ordering = ("sort", "pk")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "alt", "variant", "sort", "preview")
    readonly_fields = ("preview",)
    ordering = ("sort", "pk")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if not obj.pk or not obj.image:
            return "—"
        return format_html('<img src="{}" alt="" style="height:64px;border-radius:6px">', obj.image.url)


class ProductSpecValueInline(admin.TabularInline):
    model = ProductSpecValue
    extra = 0
    fields = ("attribute", "value_text", "value_number")
    autocomplete_fields = ("attribute",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "brand",
        "category",
        "min_price_display",
        "in_stock",
        "status",
        "discount_pct",
        "rev",
    )
    list_filter = ("status", "in_stock", "brand", "category")
    search_fields = ("title", "slug", "brand__name_fa", "variants__sku")
    ordering = ("-created_at",)
    inlines = (VariantInline, ProductImageInline, ProductSpecValueInline)
    autocomplete_fields = ("brand", "category")
    readonly_fields = (
        "min_price",
        "max_price",
        "compare_at_min",
        "discount_pct",
        "in_stock",
        "total_stock",
        "rev",
        "search_text",
        "category_path",
        "created_at",
        "updated_at",
    )
    actions = ("action_activate", "action_archive")
    fieldsets = (
        (None, {"fields": ("title", "slug", "brand", "category", "status")}),
        ("محتوا", {"fields": ("short_description", "description", "warranty_text")}),
        ("تصویر", {"fields": ("main_image",)}),
        ("سئو", {"fields": ("seo_title", "seo_description"), "classes": ("collapse",)}),
        (
            "محاسبه‌شده",
            {
                "fields": (
                    "min_price",
                    "max_price",
                    "compare_at_min",
                    "discount_pct",
                    "in_stock",
                    "total_stock",
                    "category_path",
                    "rev",
                    "search_text",
                ),
                "classes": ("collapse",),
            },
        ),
        ("سایر", {"fields": ("is_demo", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("brand", "category")

    @admin.display(description="کمترین قیمت")
    def min_price_display(self, obj) -> str:
        return f"{obj.min_price:,}"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        product = form.instance

        if not product.variants.exists():
            Variant.objects.create(
                product=product,
                sku=f"SKU-{product.pk}",
                title="پیش‌فرض",
                price=product.min_price or 0,
                stock=0,
                max_per_order=None,
            )
            messages.info(request, "یک تنوع پیش‌فرض برای محصول ساخته شد.")

        first_image = product.images.order_by("sort", "pk").first()
        if first_image and product.main_image_id != first_image.pk:
            product.main_image = first_image
            product.save(update_fields=["main_image", "updated_at"])

        product.refresh_aggregates()

    @admin.action(description="فعال‌سازی محصولات انتخاب‌شده")
    def action_activate(self, request, queryset):
        count = queryset.update_tracked(status=Product.STATUS_ACTIVE)
        self.message_user(request, f"{count} محصول فعال شد.", messages.SUCCESS)

    @admin.action(description="بایگانی محصولات انتخاب‌شده")
    def action_archive(self, request, queryset):
        count = queryset.update_tracked(status=Product.STATUS_ARCHIVED)
        self.message_user(request, f"{count} محصول بایگانی شد.", messages.SUCCESS)


@admin.register(SpecAttribute)
class SpecAttributeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "type", "unit", "is_filterable", "sort")
    list_filter = ("type", "is_filterable", "category")
    search_fields = ("name",)
    ordering = ("category", "sort", "pk")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("variant", "delta", "reason", "note", "created_at")
    list_filter = ("reason",)
    search_fields = ("variant__sku", "variant__product__title", "note")
    ordering = ("-created_at",)
    readonly_fields = ("variant", "delta", "reason", "order_item_id", "note", "created_at", "updated_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


admin.site.register(ProductImage)
