"""Order admin: read-only data, staff status moves through the workflow, refund report, invoice (docs/02 §7, §12)."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path

from apps.core.jalali import jalali_str
from apps.core.text import format_toman
from apps.orders import notify, workflow
from apps.orders.invoice import render_invoice
from apps.orders.models import PAID_STATES, Order, OrderItem, OrderStatusLog, ShippingMethod
from apps.payments import services as payment_services
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
    readonly_fields = ("created_at",)  # non-editable: excluded from the form, still shown


class OrderStatusLogInline(_ReadOnlyInline):
    model = OrderStatusLog
    fields = ("from_status", "to_status", "note", "created_at")
    readonly_fields = ("created_at",)


class StatusForm(forms.Form):
    to_status = forms.ChoiceField(label="وضعیت جدید")
    tracking_code = forms.CharField(
        label="کد رهگیری",
        required=False,
        max_length=workflow.MAX_TRACKING_LENGTH,
        help_text="برای «ارسال‌شده» با روش دارای رهگیری الزامی است",
    )
    note = forms.CharField(label="یادداشت داخلی", required=False, max_length=200)

    def __init__(self, *args, order, **kwargs):
        super().__init__(*args, **kwargs)
        labels = dict(Order.STATUS_CHOICES)
        self.fields["to_status"].choices = [(s, labels[s]) for s in workflow.allowed_targets(order)]
        self.fields["tracking_code"].initial = order.tracking_code


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "buyer_name",
        "buyer_mobile",
        "status",
        "payable_display",
        "created_jalali",
        "tracking_code",
    )
    list_filter = ("status", ("created_at", admin.DateFieldListFilter))
    search_fields = ("number", "buyer_mobile", "recipient_mobile", "tracking_code")
    ordering = ("-created_at", "-id")
    inlines = (OrderItemInline, PaymentInline, OrderStatusLogInline)
    actions = ("mark_processing", "mark_delivered", "resend_status_sms")
    fieldsets = (
        (
            "سفارش",
            {
                "fields": (
                    "number",
                    "status",
                    "tracking_code",
                    "created_at",
                    "paid_at",
                    "reserved_until",
                    "cancelled_at",
                    "cancel_reason",
                )
            },
        ),
        ("مبالغ", {"fields": ("items_total", "shipping_cost", "payable")}),
        ("خریدار", {"fields": ("user", "buyer_name", "buyer_mobile", "buyer_national_code", "buyer_email")}),
        (
            "گیرنده و آدرس",
            {
                "fields": (
                    "recipient_name",
                    "recipient_mobile",
                    "province_name",
                    "city_name",
                    "address_text",
                    ("plate", "unit"),
                    "postal_code",
                    ("lat", "lng"),
                )
            },
        ),
        ("ارسال", {"fields": ("shipping_method_title", "shipping_payment_mode")}),
    )

    # data is read-only; status moves go through the workflow only
    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def has_manage_permission(self, request) -> bool:
        return request.user.has_perm("orders.manage_order_status")

    @admin.display(description="مبلغ (تومان)", ordering="payable")
    def payable_display(self, obj) -> str:
        return format_toman(obj.payable)

    @admin.display(description="ثبت", ordering="created_at")
    def created_jalali(self, obj) -> str:
        return jalali_str(obj.created_at)

    def changelist_view(self, request, extra_context=None):
        count = payment_services.refund_candidates().count()
        if count:
            messages.warning(
                request,
                f"{count} پرداخت تاییدشده روی سفارش لغو یا منقضی نیاز به بازگشت وجه دارد "
                "(فیلتر «نیازمند بازگشت وجه» در بخش پرداخت‌ها).",
            )
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        order = self.get_object(request, object_id)
        extra = {
            "can_manage": self.has_manage_permission(request),
            "has_targets": bool(order and workflow.allowed_targets(order)),
            "can_invoice": bool(order and order.status in PAID_STATES),
        }
        return super().change_view(request, object_id, form_url, {**(extra_context or {}), **extra})

    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/status/",
                self.admin_site.admin_view(self.status_view),
                name="orders_order_status",
            ),
            path(
                "<path:object_id>/invoice/",
                self.admin_site.admin_view(self.invoice_view),
                name="orders_order_invoice",
            ),
        ]
        return custom + super().get_urls()

    def status_view(self, request, object_id):
        if not self.has_manage_permission(request):
            raise PermissionDenied
        order = get_object_or_404(Order, pk=object_id)
        form = StatusForm(request.POST or None, order=order)
        if request.method == "POST" and form.is_valid():
            try:
                workflow.change_status(
                    order.pk,
                    form.cleaned_data["to_status"],
                    by=request.user,
                    tracking_code=form.cleaned_data["tracking_code"],
                    note=form.cleaned_data["note"],
                )
            except workflow.TransitionError as exc:
                form.add_error(None, str(exc))
            else:
                self.message_user(request, "وضعیت سفارش تغییر کرد.", messages.SUCCESS)
                return redirect("admin:orders_order_change", order.pk)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "order": order,
            "form": form,
            "title": f"تغییر وضعیت {order.number}",
        }
        return render(request, "admin/orders/order/change_status.html", context)

    def invoice_view(self, request, object_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        order = get_object_or_404(Order.objects.prefetch_related("items"), pk=object_id, status__in=PAID_STATES)
        return render_invoice(request, order)

    def _bulk(self, request, queryset, to: str) -> None:
        done = failed = 0
        for pk in list(queryset.values_list("pk", flat=True)):
            try:
                workflow.change_status(pk, to, by=request.user)
                done += 1
            except workflow.TransitionError:
                failed += 1
        self.message_user(
            request,
            f"{done} سفارش تغییر کرد، {failed} مورد مجاز نبود.",
            messages.SUCCESS if not failed else messages.WARNING,
        )

    @admin.action(description="شروع آماده‌سازی (پرداخت‌شده ← در حال آماده‌سازی)", permissions=["manage"])
    def mark_processing(self, request, queryset):
        self._bulk(request, queryset, Order.PROCESSING)

    @admin.action(description="ثبت تحویل (ارسال‌شده ← تحویل‌شده)", permissions=["manage"])
    def mark_delivered(self, request, queryset):
        self._bulk(request, queryset, Order.DELIVERED)

    @admin.action(description="ارسال دوباره‌ی پیامک وضعیت فعلی", permissions=["manage"])
    def resend_status_sms(self, request, queryset):
        for pk in list(queryset.values_list("pk", flat=True)):
            notify.send_status_sms(pk)
        self.message_user(request, "پیامک‌ها ارسال شد (نتیجه در لاگ پیامک).", messages.SUCCESS)
