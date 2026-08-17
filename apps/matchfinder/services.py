import uuid
from collections import Counter

from django.db.models import F
from django.utils import timezone

from apps.specialists.models import Specialist

from .models import MatchResult, MatchResultItem, QuizResponse


def new_run_token():
    return uuid.uuid4()


def _identity_kwargs(request):
    if request.user.is_authenticated:
        return {"user": request.user}
    if not request.session.session_key:
        request.session.save()
    return {"session_key": request.session.session_key}


def owns_run(request, run_token):
    """A run_token is unguessable (UUID), so the first request to touch it
    implicitly claims it — record_response() always stamps the current
    identity. This just checks a *later* request against whoever answered
    first, so one visitor's in-progress run can't be hijacked by someone
    who spots the URL in, say, shared browser history."""
    first_response = QuizResponse.objects.filter(run_token=run_token).first()
    if not first_response:
        return True
    if first_response.user_id:
        return request.user.is_authenticated and request.user.id == first_response.user_id
    return (
        bool(first_response.session_key)
        and first_response.session_key == request.session.session_key
    )


def record_response(request, run_token, question, choice):
    QuizResponse.objects.update_or_create(
        run_token=run_token,
        question=question,
        defaults={"choice": choice, **_identity_kwargs(request)},
    )


def _ordered_candidates(queryset):
    return queryset.order_by(
        "-average_rating",
        F("next_available_date").asc(nulls_last=True),
        F("hourly_rate").asc(nulls_last=True),
    )


def _build_reason(specialist, matched_tag):
    reason = (
        f"متخصص/ة في {matched_tag.name}"
        if matched_tag
        else "من الأخصائيين الأعلى تقييماً على المنصة"
    )
    if specialist.next_available_date:
        days_away = (specialist.next_available_date - timezone.localdate()).days
        if days_away <= 0:
            reason += "، متاح/ة اليوم"
        elif days_away <= 3:
            reason += "، متاح/ة خلال الأيام القادمة"
    return reason + "."


def generate_match_result(request, run_token):
    """Rule-based (no ML/LLM): tally which specialty tag the visitor's
    answers point at most, rank approved specialists in that specialty by
    rating/availability/price, and backfill with other top-rated approved
    specialists if fewer than 3 match the tag directly."""
    responses = QuizResponse.objects.filter(run_token=run_token).select_related(
        "choice__maps_to_specialty"
    )
    tag_counts = Counter(
        r.choice.maps_to_specialty for r in responses if r.choice.maps_to_specialty_id
    )
    top_tag = tag_counts.most_common(1)[0][0] if tag_counts else None

    approved = Specialist.objects.filter(status="approved")
    picks = []
    picked_ids = set()

    if top_tag:
        for specialist in _ordered_candidates(approved.filter(specialties=top_tag))[:3]:
            picks.append((specialist, top_tag))
            picked_ids.add(specialist.pk)

    if len(picks) < 3:
        backfill = _ordered_candidates(approved.exclude(pk__in=picked_ids))[: 3 - len(picks)]
        picks.extend((specialist, None) for specialist in backfill)

    match_result = MatchResult.objects.create(
        run_token=run_token, recommended_specialty=top_tag, **_identity_kwargs(request)
    )
    MatchResultItem.objects.bulk_create(
        [
            MatchResultItem(
                match_result=match_result,
                specialist=specialist,
                reason=_build_reason(specialist, matched_tag),
                rank=rank,
            )
            for rank, (specialist, matched_tag) in enumerate(picks)
        ]
    )
    return match_result
