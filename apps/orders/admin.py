"""Read-only order admin: state changes land with the operations workflow in P6."""

from django.contrib import admin

from apps.orders.models import Order, OrderItem, OrderStatusLog, ShippingMethod
from apps.payments.models import Payment


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "payment_mode", "has_tracking", "max_weight_g", "is_active", "sort")
    list_editable = ("is_active", "sort")


class _ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


class OrderItemInline(_ReadOnlyInline):
    model = OrderItem
    fields = ("product_title", "variant_title", "sku", "unit_price", "qty")


class PaymentInline(_ReadOnlyInline):
    model = Payment
    fields = ("gateway_code", "amount", "status", "ref_id", "created_at")


class OrderStatusLogInline(_ReadOnlyInline):
    model = OrderStatusLog
    fields = ("from_status", "to_status", "note", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "payable", "created_at")
    list_filter = ("status",)
    search_fields = ("number", "buyer_mobile", "recipient_mobile")
    inlines = (OrderItemInline, PaymentInline, OrderStatusLogInline)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
