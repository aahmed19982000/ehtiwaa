from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimeStampedModel


class Tag(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    # allow_unicode=True — plain slugify() on Arabic tag names (the norm
    # here, e.g. "قلق") strips every character and yields an empty slug.
    slug = models.SlugField(unique=True, allow_unicode=True)

    def __str__(self):
        return self.name


class Question(TimeStampedModel):
    author = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="forum_questions"
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    tags = models.ManyToManyField("forum.Tag", related_name="questions", blank=True)
    views_count = models.PositiveIntegerField(default=0)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Answer(TimeStampedModel):
    question = models.ForeignKey("forum.Question", on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="forum_answers"
    )
    body = models.TextField()
    is_accepted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_accepted", "created_at"]

    def __str__(self):
        return f"Answer<{self.question_id}>"


class Vote(TimeStampedModel):
    """A single "وجدت هذا مفيداً" (found this helpful) mark — the design
    has no dislike/downvote affordance, just one helpful count per answer,
    so this is presence-based rather than a +1/-1 value."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="forum_votes")
    answer = models.ForeignKey("forum.Answer", on_delete=models.CASCADE, related_name="votes")

    class Meta:
        unique_together = [("user", "answer")]

    def __str__(self):
        return f"Vote<{self.user_id}:{self.answer_id}>"


class ContentReport(TimeStampedModel):
    """Basic moderation tool — "إبلاغ عن محتوى" — attachable to a Question
    or an Answer via contenttypes, same pattern as apps.reviews.Review."""

    STATUS_CHOICES = [("open", "open"), ("reviewed", "reviewed"), ("dismissed", "dismissed")]

    reporter = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="forum_reports"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"ContentReport<{self.content_type_id}:{self.object_id}>"
