from django.utils import timezone

from apps.specialists.models import ApprovalRequest
from apps.specialists.tasks import notify_specialist_decision_task


def approve_specialist(specialist, reviewer, notes=""):
    specialist.status = "approved"
    specialist.save(update_fields=["status"])
    ApprovalRequest.objects.create(
        specialist=specialist,
        reviewed_by=reviewer,
        decision="approved",
        notes=notes,
        decided_at=timezone.now(),
    )
    notify_specialist_decision_task.delay(specialist.pk, "approved")


def reject_specialist(specialist, reviewer, notes=""):
    specialist.status = "rejected"
    specialist.save(update_fields=["status"])
    ApprovalRequest.objects.create(
        specialist=specialist,
        reviewed_by=reviewer,
        decision="rejected",
        notes=notes,
        decided_at=timezone.now(),
    )
    notify_specialist_decision_task.delay(specialist.pk, "rejected", notes)
