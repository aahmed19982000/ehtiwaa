from django.contrib import admin

from .models import (
    ApprovalRequest,
    CredentialDocument,
    Education,
    Specialist,
    SpecialtyTag,
    WorkExperience,
)


class CredentialDocumentInline(admin.TabularInline):
    model = CredentialDocument
    extra = 0


class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    """Approving specialists (and, until the reviews/bookings apps exist,
    setting average_rating/next_available_date for the directory) happens
    here — the report defers a dedicated admin panel to a later phase."""

    list_display = [
        "full_name_ar",
        "user",
        "category",
        "status",
        "average_rating",
        "hourly_rate",
        "next_available_date",
    ]
    list_editable = ["status", "average_rating", "hourly_rate", "next_available_date"]
    list_filter = ["status", "category", "gender"]
    search_fields = ["full_name_ar", "full_name_en", "user__email"]
    inlines = [WorkExperienceInline, EducationInline, CredentialDocumentInline]


admin.site.register(SpecialtyTag)
admin.site.register(ApprovalRequest)
