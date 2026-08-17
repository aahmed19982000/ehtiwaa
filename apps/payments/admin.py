from django.contrib import admin

from .models import Invoice, Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    """Deliberately shows only `item_display` (the target's __str__) for the
    generically-related item — never reach into a specific model's fields
    here (e.g. a linked bookings.Booking's `notes`). Finance Manager has
    full access to Order/OrderItem but no Booking permission at all; adding
    a field here that surfaces Booking internals would defeat that
    field-level restriction (see apps.bookings.admin.BookingAdmin)."""

    model = OrderItem
    extra = 0
    fields = ["content_type", "item_display", "quantity", "unit_price", "line_total"]
    readonly_fields = ["item_display"]

    @admin.display(description="العنصر")
    def item_display(self, obj):
        return str(obj.item) if obj.item else "—"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total", "created_at"]
    list_editable = ["status"]
    list_filter = ["status"]
    search_fields = ["user__email"]
    inlines = [OrderItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "method", "status", "provider_reference", "paid_at"]
    list_editable = ["status"]
    list_filter = ["status", "method"]
    search_fields = ["order__user__email", "provider_reference"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "order", "vat_rate", "issued_at"]
    search_fields = ["invoice_number", "order__user__email"]
