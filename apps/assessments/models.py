import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class Assessment(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    # Filter-chip topic on the listing page (e.g. "قلق", "اكتئاب") — free
    # text, same simplification as courses.Course.category.
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=5)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @property
    def questions_count(self):
        return self.questions.count()


class Question(TimeStampedModel):
    """Distinct from forum.Question — separate app, separate DB table
    (assessments_question vs forum_question), no naming collision."""

    assessment = models.ForeignKey(
        "assessments.Assessment", on_delete=models.CASCADE, related_name="questions"
    )
    text = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class AnswerOption(TimeStampedModel):
    """Typically a 5-point Likert scale (أبداً..دائماً, score_value 0-4) —
    not enforced in the model so admins stay free to configure fewer/more
    options per question."""

    question = models.ForeignKey(
        "assessments.Question", on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=255)
    score_value = models.IntegerField(default=0)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class ScoreLevel(TimeStampedModel):
    """Admin-configurable scoring thresholds per assessment — total_score
    falling within [min_score, max_score] maps an Attempt to this level."""

    LEVEL_CHOICES = [
        ("low", "منخفض"),
        ("medium", "متوسط"),
        ("high", "مرتفع"),
    ]

    assessment = models.ForeignKey(
        "assessments.Assessment", on_delete=models.CASCADE, related_name="score_levels"
    )
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    min_score = models.IntegerField()
    max_score = models.IntegerField()
    description = models.TextField(
        help_text="النص الإرشادي المعروض للمستخدم عند وقوعه في هذا المستوى."
    )

    class Meta:
        ordering = ["min_score"]
        unique_together = [("assessment", "level")]

    def __str__(self):
        return f"{self.assessment.title} — {self.get_level_display()}"


class Attempt(TimeStampedModel):
    # Exactly one of these identifies who's taking the assessment — a
    # logged-in user's attempt follows their account, an anonymous
    # visitor's is scoped to their session. Same pattern as store.Cart.
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assessment_attempts",
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    assessment = models.ForeignKey(
        "assessments.Assessment", on_delete=models.CASCADE, related_name="attempts"
    )
    # Opaque public identifier for the take/result URLs — a sequential pk
    # would let anyone enumerate other visitors' psychological test
    # results just by incrementing a number in the URL.
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    selected_options = models.ManyToManyField(
        "assessments.AnswerOption", related_name="attempts", blank=True
    )
    total_score = models.IntegerField(null=True, blank=True)
    result_level = models.ForeignKey(
        "assessments.ScoreLevel", on_delete=models.SET_NULL, null=True, blank=True
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name="assessments_attempt_has_user_or_session",
            )
        ]

    def __str__(self):
        return f"Attempt<{self.user_id or self.session_key}:{self.assessment_id}>"
