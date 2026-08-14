from django.db import models

from apps.core.models import TimeStampedModel

# Admin roles are modeled with Django's built-in Group/Permission system
# rather than a custom model — seeded via fixtures/data migration in a
# later phase when RBAC is actually implemented.


class Report(TimeStampedModel):
    REPORT_TYPE_CHOICES = [
        ("payments", "payments"),
        ("bookings", "bookings"),
        ("users", "users"),
    ]

    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    generated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_reports",
    )
    date_from = models.DateField()
    date_to = models.DateField()
    file = models.FileField(upload_to="reports/", null=True, blank=True)

    def __str__(self):
        return f"Report<{self.report_type}:{self.date_from}-{self.date_to}>"
