from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.services import send_notification_email, send_whatsapp_stub


@shared_task
def notify_specialist_decision_task(specialist_id, decision, notes=""):
    from .models import Specialist

    specialist = Specialist.objects.select_related("user").get(pk=specialist_id)
    user = specialist.user

    if decision == "approved":
        send_notification_email(
            user,
            "specialists/email/application_approved_subject.txt",
            "specialists/email/application_approved.txt",
            {"specialist": specialist},
        )
        send_whatsapp_stub(user, "مبروك! تم اعتماد طلب انضمامك كأخصائي على منصة احتواء.")
        Notification.objects.create(
            user=user,
            title="تم اعتماد طلبك كأخصائي",
            body="تهانينا! أصبح ملفك التعريفي ظاهرًا الآن في دليل الأخصائيين.",
            notif_type="system",
        )
    else:
        send_notification_email(
            user,
            "specialists/email/application_rejected_subject.txt",
            "specialists/email/application_rejected.txt",
            {"specialist": specialist, "notes": notes},
        )
        send_whatsapp_stub(user, "نأسف، تعذّر اعتماد طلب انضمامك كأخصائي حاليًا.")
        Notification.objects.create(
            user=user,
            title="تحديث بخصوص طلب الانضمام كأخصائي",
            body="نأسف، تعذّر اعتماد طلبك حاليًا. راجع بريدك الإلكتروني للتفاصيل.",
            notif_type="system",
        )
