from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.notifications.models import MessageLog


@shared_task
def notify_team_new_ticket_task(ticket_id):
    """Emails the support team and logs a WhatsApp notification stub — no
    WhatsApp Business API provider is configured yet (needs a real Meta
    Business account), same stopgap as apps.notifications.services'
    send_whatsapp_stub."""
    from .models import SupportTicket

    ticket = SupportTicket.objects.select_related("category", "user").get(pk=ticket_id)
    subject = f"تذكرة دعم جديدة: {ticket.subject}"
    body = render_to_string("support/email/new_ticket_notification.txt", {"ticket": ticket})
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.SUPPORT_TEAM_EMAIL])

    MessageLog.objects.create(
        user=ticket.user,
        channel="whatsapp",
        recipient=settings.SUPPORT_WHATSAPP_NUMBER or "(not configured)",
        subject=subject[:255],
        status="failed",
        provider_response=(
            "No WhatsApp Business API provider configured yet — see "
            "apps.support.tasks.notify_team_new_ticket_task."
        ),
    )
