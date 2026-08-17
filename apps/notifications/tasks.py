from celery import shared_task

from .models import Notification
from .services import send_notification_email, send_whatsapp_stub


@shared_task
def notify_booking_created_task(booking_id):
    from apps.bookings.models import Booking

    booking = Booking.objects.select_related("client", "specialist").get(pk=booking_id)
    send_notification_email(
        booking.client,
        "bookings/email/booking_confirmation_subject.txt",
        "bookings/email/booking_confirmation.txt",
        {"booking": booking},
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


@shared_task
def notify_booking_payment_confirmed_task(booking_id):
    from apps.bookings.models import Booking

    booking = Booking.objects.select_related("client", "specialist").get(pk=booking_id)
    send_notification_email(
        booking.client,
        "bookings/email/booking_payment_confirmed_subject.txt",
        "bookings/email/booking_payment_confirmed.txt",
        {"booking": booking},
    )
    send_whatsapp_stub(
        booking.client, f"تم تأكيد حجزك مع {booking.specialist.full_name_ar} بعد إتمام الدفع."
    )
    Notification.objects.create(
        user=booking.client,
        title="تم تأكيد حجزك",
        body=f"تم تأكيد حجزك مع {booking.specialist.full_name_ar} بعد إتمام الدفع بنجاح.",
        notif_type="booking",
    )


@shared_task
def notify_booking_cancelled_task(booking_id):
    from apps.bookings.models import Booking

    booking = Booking.objects.select_related("client", "specialist").get(pk=booking_id)
    send_notification_email(
        booking.client,
        "bookings/email/booking_cancelled_subject.txt",
        "bookings/email/booking_cancelled.txt",
        {"booking": booking},
    )
    send_whatsapp_stub(booking.client, f"تم إلغاء حجزك مع {booking.specialist.full_name_ar}.")
    Notification.objects.create(
        user=booking.client,
        title="تم إلغاء حجزك",
        body=f"تم إلغاء حجزك مع {booking.specialist.full_name_ar}.",
        notif_type="booking",
    )
