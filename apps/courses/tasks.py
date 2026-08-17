from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.services import send_notification_email, send_whatsapp_stub


@shared_task
def notify_enrollment_created_task(enrollment_id):
    from .models import Enrollment

    enrollment = Enrollment.objects.select_related("user", "course").get(pk=enrollment_id)
    send_notification_email(
        enrollment.user,
        "courses/email/enrollment_confirmation_subject.txt",
        "courses/email/enrollment_confirmation.txt",
        {"enrollment": enrollment},
    )
    send_whatsapp_stub(enrollment.user, f"تم تفعيل وصولك لدورة {enrollment.course.title}.")
    Notification.objects.create(
        user=enrollment.user,
        title="تم تفعيل اشتراكك في الدورة",
        body=f"يمكنك الآن الوصول لمحتوى دورة {enrollment.course.title}.",
        notif_type="course",
    )


@shared_task
def notify_certificate_issued_task(enrollment_id):
    from .models import Enrollment

    enrollment = Enrollment.objects.select_related("user", "course").get(pk=enrollment_id)
    send_notification_email(
        enrollment.user,
        "courses/email/certificate_issued_subject.txt",
        "courses/email/certificate_issued.txt",
        {"enrollment": enrollment},
    )
    Notification.objects.create(
        user=enrollment.user,
        title="مبروك! حصلت على شهادة إتمام",
        body=f"أتممت دورة {enrollment.course.title} بنجاح — شهادتك جاهزة للتحميل.",
        notif_type="course",
    )
