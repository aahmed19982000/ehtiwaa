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

    def __str__(self):
        return f"Specialist<{self.user_id}>"


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
