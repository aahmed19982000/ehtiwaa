from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import MessageLog, Notification


def send_notification_email(user, subject_template, body_template, context):
    """Renders + sends an email and records it in MessageLog either way, so
    delivery failures are visible in the admin instead of silently lost."""
    subject = render_to_string(subject_template, context).strip()
    body = render_to_string(body_template, context)
    log = MessageLog.objects.create(
        user=user, channel="email", recipient=user.email, subject=subject, status="queued"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception as exc:  # noqa: BLE001 — SMTP backends raise all sorts (smtplib, socket, ssl); MessageLog exists specifically to capture whichever one happened.
        log.status = "failed"
        log.provider_response = str(exc)
        log.save(update_fields=["status", "provider_response"])
        return
    log.status = "sent"
    log.save(update_fields=["status"])


def send_whatsapp_stub(user, message):
    """No WhatsApp provider (Twilio / Meta Cloud API) is wired up yet — this
    just records the intended message in MessageLog so the call sites and
    audit trail are already in place for when a provider is added."""
    MessageLog.objects.create(
        user=user,
        channel="whatsapp",
        recipient=user.phone or "",
        subject=message[:255],
        status="failed",
        provider_response=(
            "No WhatsApp provider configured — see apps.notifications.services.send_whatsapp_stub."
        ),
    )


def notify_booking_created(booking):
    context = {"booking": booking}
    send_notification_email(
        booking.client,
        "bookings/email/booking_confirmation_subject.txt",
        "bookings/email/booking_confirmation.txt",
        context,
    )
    send_whatsapp_stub(
        booking.client,
        f"تم استلام طلب حجزك مع {booking.specialist.full_name_ar} — بانتظار التأكيد.",
    )
    Notification.objects.create(
        user=booking.client,
        title="تم استلام طلب حجزك",
        body=f"طلب حجزك مع {booking.specialist.full_name_ar} قيد المراجعة.",
        notif_type="booking",
    )


def notify_booking_cancelled(booking):
    context = {"booking": booking}
    send_notification_email(
        booking.client,
        "bookings/email/booking_cancelled_subject.txt",
        "bookings/email/booking_cancelled.txt",
        context,
    )
    send_whatsapp_stub(
        booking.client,
        f"تم إلغاء حجزك مع {booking.specialist.full_name_ar}.",
    )
    Notification.objects.create(
        user=booking.client,
        title="تم إلغاء حجزك",
        body=f"تم إلغاء حجزك مع {booking.specialist.full_name_ar}.",
        notif_type="booking",
    )
