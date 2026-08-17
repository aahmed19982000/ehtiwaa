from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel

LANGUAGE_CHOICES = [
    ("ar", _("العربية")),
    ("en", _("الإنجليزية")),
    ("fr", _("الفرنسية")),
    ("de", _("الألمانية")),
    ("es", _("الإسبانية")),
    ("it", _("الإيطالية")),
    ("tr", _("التركية")),
    ("ur", _("الأردية")),
    ("zh", _("الصينية")),
]


class SpecialtyTag(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Specialist(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("approved", "approved"),
        ("rejected", "rejected"),
        ("suspended", "suspended"),
    ]
    CATEGORY_CHOICES = [
        ("psychiatrist", _("طبيب نفسي")),
        ("clinical_psychologist", _("معالج نفسي اكلينيكي")),
        ("counselor", _("مرشد نفسي")),
    ]
    TITLE_CHOICES = [
        ("mr", _("سيد")),
        ("mrs", _("سيدة")),
        ("ms", _("آنسة")),
        ("dr", _("دكتور")),
    ]
    GENDER_CHOICES = [("male", _("ذكر")), ("female", _("أنثى"))]

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="specialist_profile"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    license_number = models.CharField(max_length=100, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    headline = models.CharField(max_length=255, blank=True)
    about = models.TextField(blank=True)
    specialties = models.ManyToManyField(
        "specialists.SpecialtyTag", related_name="specialists", blank=True
    )
    # hourly_rate is the 60-minute session price (also what the directory's
    # price filter/sort use); price_30min is the shorter tier shown on the
    # profile page alongside it.
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_30min = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # Denormalized directory/profile sort-display fields — the reviews and
    # bookings apps (later phases) will compute these for real; until then
    # they're plain admin-editable fields, matching the report's guidance to
    # rely on the default Django Admin for temporary tracking at this phase.
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    next_available_date = models.DateField(null=True, blank=True)
    completed_sessions_count = models.PositiveIntegerField(default=0)

    # Application-form fields (apps.specialists application flow)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    full_name_ar = models.CharField(max_length=255, blank=True)
    full_name_en = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    country_of_residence = models.CharField(max_length=100, blank=True)
    languages = ArrayField(models.CharField(max_length=50), default=list, blank=True)

    def __str__(self):
        return f"Specialist<{self.user_id}>"

    def get_languages_display(self):
        labels = dict(LANGUAGE_CHOICES)
        return [labels.get(code, code) for code in self.languages]


class WorkExperience(TimeStampedModel):
    """One entry in the specialist's CV-style work history, shown on their
    profile page (job title, institution, date range)."""

    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.CASCADE, related_name="work_experiences"
    )
    job_title = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # blank = "الآن" (current)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.job_title} @ {self.institution}"


class Education(TimeStampedModel):
    """One entry in the specialist's education history, shown on their
    profile page (degree, institution, date range)."""

    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.CASCADE, related_name="education_entries"
    )
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.degree} @ {self.institution}"


class CredentialDocument(TimeStampedModel):
    """A single uploaded credential file from the specialist application form
    (degree certificate, license, syndicate card, supervision proof, ...).
    Kept generic (label + file) rather than one field per document type since
    the required set differs per Specialist.category."""

    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.CASCADE, related_name="credential_documents"
    )
    label = models.CharField(max_length=255)
    file = models.FileField(upload_to="specialists/credentials/")

    def __str__(self):
        return f"CredentialDocument<{self.specialist_id}:{self.label}>"


class ApprovalRequest(TimeStampedModel):
    DECISION_CHOICES = [
        ("pending", "pending"),
        ("approved", "approved"),
        ("rejected", "rejected"),
    ]

    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.CASCADE, related_name="approval_requests"
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_approval_requests",
    )
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ApprovalRequest<{self.specialist_id}>"
