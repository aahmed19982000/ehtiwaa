import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class QuizQuestion(TimeStampedModel):
    text = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class QuizChoice(TimeStampedModel):
    """One selectable answer for a QuizQuestion. The specialty mapping lives
    here (per choice), not on the question — different answers to the same
    question point at different specialties, which is what the rule engine
    tallies up (see apps.matchfinder.services)."""

    question = models.ForeignKey(
        "matchfinder.QuizQuestion", on_delete=models.CASCADE, related_name="choices"
    )
    label = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    maps_to_specialty = models.ForeignKey(
        "specialists.SpecialtyTag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quiz_choices",
        help_text="فارغ لخيار عام مثل 'غير ذلك' لا يحدد تخصصاً بعينه.",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class QuizResponse(TimeStampedModel):
    # Exactly one of user/session_key identifies who answered — same
    # pattern as store.Cart / assessments.Attempt.
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quiz_responses",
    )
    session_key = models.CharField(max_length=40, blank=True)
    # Groups every answer from one wizard pass together — a visitor can run
    # the finder more than once, each run scored independently.
    run_token = models.UUIDField(default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        "matchfinder.QuizQuestion", on_delete=models.CASCADE, related_name="responses"
    )
    choice = models.ForeignKey(
        "matchfinder.QuizChoice", on_delete=models.CASCADE, related_name="responses"
    )

    class Meta:
        unique_together = [("run_token", "question")]

    def __str__(self):
        return f"QuizResponse<{self.run_token}:{self.question_id}>"


class MatchResult(TimeStampedModel):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="match_results",
    )
    session_key = models.CharField(max_length=40, blank=True)
    # Opaque public identifier for the results URL — same reasoning as
    # assessments.Attempt.share_token (avoids enumerable sequential IDs).
    run_token = models.UUIDField(unique=True, editable=False)
    recommended_specialty = models.ForeignKey(
        "specialists.SpecialtyTag",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_results",
    )

    def __str__(self):
        return f"MatchResult<{self.run_token}>"


class MatchResultItem(TimeStampedModel):
    """One recommended specialist within a MatchResult, carrying its own
    generated "reason" text — a plain M2M can't hold that per-pairing data."""

    match_result = models.ForeignKey(
        "matchfinder.MatchResult", on_delete=models.CASCADE, related_name="items"
    )
    specialist = models.ForeignKey(
        "specialists.Specialist", on_delete=models.CASCADE, related_name="match_result_items"
    )
    reason = models.TextField(blank=True)
    rank = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["rank"]
        unique_together = [("match_result", "specialist")]

    def __str__(self):
        return f"MatchResultItem<{self.match_result_id}:{self.specialist_id}>"
