from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import MessageLog


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
    except Exception as exc:  # noqa: BLE001 — SMTP backends raise all sorts; MessageLog captures it
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
