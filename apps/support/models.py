from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models

from apps.core.models import TimeStampedModel


class HelpCategory(TimeStampedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, allow_unicode=True)
    # Single glyph/emoji shown in the category icon circle — falls back to
    # the category's first letter in the template if left blank.
    icon = models.CharField(max_length=10, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name_plural = "Help categories"

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
    # Populated in save() via a Postgres SearchVector (question weighted
    # above answer) — the report calls out GIN-indexed full-text search
    # specifically as a reason to run Postgres, this is that.
    search_vector = SearchVectorField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["order", "id"]
        indexes = [GinIndex(fields=["search_vector"])]

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # config="simple" (no stemming) — matched by services.search_faqs'
        # SearchQuery, and safer than a language-specific config across
        # mixed Arabic/English support content.
        FAQItem.objects.filter(pk=self.pk).update(
            search_vector=SearchVector("question", weight="A", config="simple")
            + SearchVector("answer", weight="B", config="simple")
        )


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
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class SupportTicket(TimeStampedModel):
    STATUS_CHOICES = [
        ("open", "open"),
        ("in_progress", "in_progress"),
        ("resolved", "resolved"),
        ("closed", "closed"),
    ]

    # Nullable — the ticket form (matching the design) accepts submissions
    # from guests, not just logged-in users. full_name/email are always
    # captured directly on the ticket either way, so support can act on it
    # without needing an account to exist.
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    category = models.ForeignKey(
        "support.HelpCategory", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    attachment = models.FileField(upload_to="support/attachments/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    def __str__(self):
        return self.subject
