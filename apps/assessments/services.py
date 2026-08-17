from django.db.models import Sum
from django.utils import timezone

from .models import Attempt


def start_attempt(request, assessment):
    """Always creates a fresh Attempt — no resume-in-progress support (kept
    simple; a user can just retake from question 1)."""
    if request.user.is_authenticated:
        return Attempt.objects.create(user=request.user, assessment=assessment)
    if not request.session.session_key:
        request.session.save()
    return Attempt.objects.create(session_key=request.session.session_key, assessment=assessment)


def owns_attempt(request, attempt):
    if attempt.user_id:
        return request.user.is_authenticated and request.user.id == attempt.user_id
    return attempt.session_key and attempt.session_key == request.session.session_key


def record_answer(attempt, question, option):
    """Replaces any prior answer for this question with `option` — lets the
    step-by-step flow support going back and changing an answer."""
    attempt.selected_options.remove(*question.options.all())
    attempt.selected_options.add(option)


def score_attempt(attempt):
    total = attempt.selected_options.aggregate(total=Sum("score_value"))["total"] or 0
    level = attempt.assessment.score_levels.filter(
        min_score__lte=total, max_score__gte=total
    ).first()
    attempt.total_score = total
    attempt.result_level = level
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["total_score", "result_level", "completed_at"])
    return attempt
