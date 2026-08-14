from django.db import models

from apps.core.models import TimeStampedModel


class QuizQuestion(TimeStampedModel):
    text = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)
    maps_to_specialty = models.ForeignKey(
        "specialists.SpecialtyTag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quiz_questions",
    )

    def __str__(self):
        return self.text


class QuizResponse(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quiz_responses",
    )
    session_key = models.CharField(max_length=100, blank=True)  # for anonymous users
    question = models.ForeignKey(
        "matchfinder.QuizQuestion", on_delete=models.CASCADE, related_name="responses"
    )
    answer_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"QuizResponse<{self.question_id}>"


class MatchResult(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="match_results",
    )
    session_key = models.CharField(max_length=100, blank=True)
    recommended_specialists = models.ManyToManyField(
        "specialists.Specialist", related_name="match_results", blank=True
    )
    recommended_specialty = models.ForeignKey(
        "specialists.SpecialtyTag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_results",
    )

    def __str__(self):
        return f"MatchResult<{self.pk}>"
