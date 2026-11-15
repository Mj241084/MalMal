from django.contrib import admin

from apps.payments.models import Payment, PaymentGateway


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_active", "sort", "min_amount", "max_amount")
    list_editable = ("is_active", "sort")
    search_fields = ("title", "code")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("pk", "order", "gateway_code", "amount", "status", "ref_id", "created_at")
    list_filter = ("status", "gateway_code")
    search_fields = ("order__number", "authority", "ref_id")
    readonly_fields = (
        "order",
        "gateway_code",
        "amount",
        "authority",
        "ref_id",
        "card_pan_masked",
        "status",
        "request_payload",
        "verify_payload",
        "verified_at",
        "ip",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
