from django.contrib import admin, messages

from apps.payments import services
from apps.payments.models import Payment, PaymentGateway


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_active", "sort", "min_amount", "max_amount")
    list_editable = ("is_active", "sort")
    search_fields = ("title", "code")


class NeedsRefundFilter(admin.SimpleListFilter):
    title = "نیازمند بازگشت وجه"
    parameter_name = "needs_refund"

    def lookups(self, request, model_admin):
        return [("1", "بله")]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(pk__in=services.refund_candidates().values("pk"))
        return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("pk", "order", "gateway_code", "amount", "status", "ref_id", "created_at")
    list_filter = ("status", "gateway_code", NeedsRefundFilter)
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

    actions = ("mark_refunded",)

    def has_manage_permission(self, request) -> bool:
        return request.user.has_perm("orders.manage_order_status")

    @admin.action(description="ثبت بازگشت وجه انجام‌شد", permissions=["manage"])
    def mark_refunded(self, request, queryset):
        ids = list(queryset.filter(pk__in=services.refund_candidates().values("pk")).values_list("pk", flat=True))
        done = failed = 0
        for pk in ids:
            try:
                result = services.record_refund(pk, by=request.user, note="ثبت از ادمین")
            except services.RefundError:
                failed += 1
                continue
            self.log_change(request, result.payment, "بازگشت وجه ثبت شد")
            done += 1
        self.message_user(
            request,
            f"{done} پرداخت به‌عنوان بازگشت‌خورده ثبت شد، {failed} مورد مجاز نبود.",
            messages.SUCCESS if not failed else messages.WARNING,
        )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
