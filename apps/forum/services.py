from django.contrib.contenttypes.models import ContentType

from .models import ContentReport, Vote


def accept_answer(question, answer, requesting_user):
    """Only the question's author may mark an answer accepted — one
    accepted answer per question, matching the design's single "أفضل
    إجابة" badge."""
    if requesting_user != question.author:
        raise PermissionError("Only the question author can accept an answer.")
    question.answers.exclude(pk=answer.pk).update(is_accepted=False)
    answer.is_accepted = True
    answer.save(update_fields=["is_accepted"])


def toggle_helpful_vote(user, answer):
    """Returns True if the vote was just added, False if it was removed."""
    vote, created = Vote.objects.get_or_create(user=user, answer=answer)
    if not created:
        vote.delete()
        return False
    return True


def create_report(user, obj, reason=""):
    ContentReport.objects.create(
        reporter=user,
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        reason=reason,
    )
