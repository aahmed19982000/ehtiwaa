from django.db import models

from apps.core.models import TimeStampedModel


class Assessment(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    """Distinct from forum.Question — separate app, separate DB table
    (assessments_question vs forum_question), no naming collision."""

    assessment = models.ForeignKey(
        "assessments.Assessment", on_delete=models.CASCADE, related_name="questions"
    )
    text = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.text


class AnswerOption(TimeStampedModel):
    question = models.ForeignKey(
        "assessments.Question", on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=255)
    score_value = models.IntegerField(default=0)
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.text


class Attempt(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="assessment_attempts"
    )
    assessment = models.ForeignKey(
        "assessments.Assessment", on_delete=models.CASCADE, related_name="attempts"
    )
    selected_options = models.ManyToManyField(
        "assessments.AnswerOption", related_name="attempts", blank=True
    )
    total_score = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Attempt<{self.user_id}:{self.assessment_id}>"
