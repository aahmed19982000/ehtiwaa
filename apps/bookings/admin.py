from django.contrib import admin

from .models import Availability, Booking


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ["specialist", "weekday", "specific_date", "start_time", "end_time", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["is_active", "weekday"]
    search_fields = ["specialist__full_name_ar", "specialist__full_name_en"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """No payments/confirmation automation yet — moving a booking from
    pending to confirmed (or completed) is a manual admin action for now."""

    # Session notes are sensitive — the RBAC report is explicit that this
    # must be a field-level restriction, not just keeping Finance Manager
    # off the Booking admin page entirely (which the "Finance Manager"
    # group's permissions already do — see apps.adminpanel's data
    # migration). This is the backstop for any other non-superuser staff
    # who ends up with Booking change access later.
    SENSITIVE_FIELDS = ["notes", "cancellation_reason"]

    list_display = ["client", "specialist", "status", "scheduled_start", "scheduled_end"]
    list_editable = ["status"]
    list_filter = ["status"]
    search_fields = ["client__email", "specialist__full_name_ar", "contact_phone"]
    date_hierarchy = "scheduled_start"

    def get_exclude(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_exclude(request, obj)
        return self.SENSITIVE_FIELDS
