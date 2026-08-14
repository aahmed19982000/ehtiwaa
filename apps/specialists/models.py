from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import TimeStampedModel


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
        ("psychiatrist", "طبيب نفسي"),
        ("clinical_psychologist", "معالج نفسي اكلينيكي"),
        ("counselor", "مرشد نفسي"),
    ]
    TITLE_CHOICES = [("mr", "سيد"), ("mrs", "سيدة"), ("ms", "آنسة"), ("dr", "دكتور")]
    GENDER_CHOICES = [("male", "ذكر"), ("female", "أنثى")]

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
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

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
