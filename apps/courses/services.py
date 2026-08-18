import uuid

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.tasks import safe_delay

from .models import Certificate, Course, Enrollment, LessonProgress
from .tasks import notify_certificate_issued_task, notify_enrollment_created_task


def enroll_from_paid_order(order):
    """Grants course access for every Course line item on a paid Order —
    called from courses.signals once a Payment flips to "succeeded".
    get_or_create() keeps this safe to re-run (e.g. a webhook retry) without
    creating duplicate enrollments or re-sending the confirmation."""
    created = []
    for item in order.items.select_related("content_type"):
        if item.content_type.model_class() is not Course:
            continue
        enrollment, was_created = Enrollment.objects.get_or_create(
            user=order.user, course_id=item.object_id, defaults={"source_order": order}
        )
        if was_created:
            created.append(enrollment)
            safe_delay(notify_enrollment_created_task, enrollment.pk)
    return created


def mark_lesson_complete(enrollment, lesson):
    """Records the lesson as done and recomputes progress_percent from the
    LessonProgress rows — those are the source of truth, not a counter, so
    un-completing/replaying never desyncs. Issues a certificate the moment
    progress reaches 100%."""
    _progress, created = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    if not created:
        return enrollment

    total = enrollment.course.total_lessons_count
    done = enrollment.lesson_progress.count()
    enrollment.progress_percent = round(done / total * 100) if total else 0

    if enrollment.progress_percent >= 100 and not enrollment.completed_at:
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=["progress_percent", "completed_at"])
        generate_certificate(enrollment)
    else:
        enrollment.save(update_fields=["progress_percent"])

    return enrollment


def generate_certificate(enrollment):
    if hasattr(enrollment, "certificate"):
        return enrollment.certificate

    from weasyprint import HTML  # heavy import — only needed on this path

    certificate_number = (
        f"EHT-{enrollment.course_id}-{enrollment.user_id}-{uuid.uuid4().hex[:6].upper()}"
    )
    html = render_to_string(
        "courses/certificate_pdf.html",
        {"enrollment": enrollment, "certificate_number": certificate_number},
    )
    pdf_bytes = HTML(string=html).write_pdf()

    certificate = Certificate.objects.create(
        enrollment=enrollment, certificate_number=certificate_number
    )
    certificate.file.save(f"{certificate_number}.pdf", ContentFile(pdf_bytes), save=True)

    safe_delay(notify_certificate_issued_task, enrollment.pk)
    return certificate
