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
    """Approving specialists happens here — the report defers a dedicated
    admin panel to a later phase. average_rating/reviews_count are normally
    recomputed automatically by apps.reviews (kept editable here only as a
    manual override); next_available_date has no availability engine
    feeding it yet, so it stays admin-set."""

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
