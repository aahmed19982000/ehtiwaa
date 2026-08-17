from django.db import models

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    NOTIF_TYPE_CHOICES = [
        ("booking", "booking"),
        ("order", "order"),
        ("course", "course"),
        ("system", "system"),
        ("forum", "forum"),
    ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPE_CHOICES, default="system")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class MessageLog(TimeStampedModel):
    CHANNEL_CHOICES = [("email", "email"), ("whatsapp", "whatsapp"), ("sms", "sms")]
    STATUS_CHOICES = [("queued", "queued"), ("sent", "sent"), ("failed", "failed")]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_logs",
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    provider_response = models.TextField(blank=True)

    def __str__(self):
        return f"MessageLog<{self.channel}:{self.recipient}>"
