from django.db import models

from apps.core.models import TimeStampedModel


class HelpCategory(TimeStampedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class FAQItem(TimeStampedModel):
    category = models.ForeignKey(
        "support.HelpCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faqs",
    )
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.question


class KBArticle(TimeStampedModel):
    category = models.ForeignKey(
        "support.HelpCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kb_articles",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    body = models.TextField(blank=True)

    def __str__(self):
        return self.title


class SupportTicket(TimeStampedModel):
    STATUS_CHOICES = [
        ("open", "open"),
        ("in_progress", "in_progress"),
        ("resolved", "resolved"),
        ("closed", "closed"),
    ]

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="support_tickets"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    def __str__(self):
        return self.subject
