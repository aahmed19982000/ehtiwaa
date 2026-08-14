from django.db import models

from apps.core.models import TimeStampedModel

WEEKDAY_CHOICES = [
    (0, "mon"),
    (1, "tue"),
    (2, "wed"),
    (3, "thu"),
    (4, "fri"),
    (5, "sat"),
    (6, "sun"),
]


class Availability(TimeStampedModel):
    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.CASCADE, related_name="availability_slots"
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES, null=True, blank=True)
    specific_date = models.DateField(null=True, blank=True)  # one-off override
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Availability<{self.specialist_id}>"


class Booking(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("confirmed", "confirmed"),
        ("completed", "completed"),
        ("cancelled", "cancelled"),
        ("no_show", "no_show"),
    ]

    client = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="bookings_as_client"
    )
    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.PROTECT, related_name="bookings"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_bookings",
    )

    def __str__(self):
        return f"Booking<{self.client_id}->{self.specialist_id}>"
