from datetime import datetime, timedelta

from django.utils import timezone

from .models import Availability, Booking

SLOT_LOOKAHEAD_DAYS = 14


def get_slots_for_date(specialist, target_date, duration_minutes=60):
    """[{'start', 'end', 'value', 'label', 'status'}, ...] for one day, built
    from the specialist's Availability windows — a specific_date override
    takes priority over the matching recurring weekday — minus existing
    pending/confirmed Bookings. Past slots for today are dropped."""
    windows = Availability.objects.filter(
        specialist=specialist, is_active=True, specific_date=target_date
    )
    if not windows.exists():
        windows = Availability.objects.filter(
            specialist=specialist,
            is_active=True,
            specific_date__isnull=True,
            weekday=target_date.weekday(),
        )

    booked_ranges = list(
        Booking.objects.filter(
            specialist=specialist,
            status__in=["pending", "confirmed"],
            scheduled_start__date=target_date,
        ).values_list("scheduled_start", "scheduled_end")
    )

    now = timezone.now()
    step = timedelta(minutes=duration_minutes)
    slots = []
    seen_starts = set()

    for window in windows:
        current = timezone.make_aware(datetime.combine(target_date, window.start_time))
        window_end = timezone.make_aware(datetime.combine(target_date, window.end_time))
        while current + step <= window_end:
            slot_end = current + step
            if current > now and current not in seen_starts:
                seen_starts.add(current)
                is_booked = any(
                    current < b_end and slot_end > b_start for b_start, b_end in booked_ranges
                )
                slots.append(
                    {
                        "start": current,
                        "end": slot_end,
                        "value": current.strftime("%Y-%m-%dT%H:%M"),
                        "label": current.strftime("%H:%M"),
                        "status": "booked" if is_booked else "available",
                    }
                )
            current += step

    slots.sort(key=lambda s: s["start"])
    return slots


def get_session_duration_minutes(specialist):
    """Which session length this specialist's slots are generated in.
    Prefers the 60-minute tier (hourly_rate) when both are priced — picking
    a duration per-booking is left for a later iteration."""
    return 60 if specialist.hourly_rate else 30


def get_session_price(specialist):
    duration = get_session_duration_minutes(specialist)
    return specialist.hourly_rate if duration == 60 else specialist.price_30min


def confirm_bookings_from_paid_order(order):
    """Moves every still-pending Booking in this paid Order to confirmed —
    called from apps.payments.services.handle_payment_succeeded. The
    Google Meet link is deliberately created here, not at booking-request
    time: generating a calendar invite for a session nobody has paid for
    yet would clutter the specialist's calendar with sessions that may
    never happen."""
    from apps.notifications.tasks import notify_booking_payment_confirmed_task

    from . import google_calendar
    from .models import Booking

    for item in order.items.select_related("content_type"):
        if item.content_type.model_class() is not Booking:
            continue
        booking = item.item
        if booking.status != "pending":
            continue

        booking.status = "confirmed"
        meet_link, event_id = google_calendar.create_meeting_for_booking(booking)
        update_fields = ["status"]
        if meet_link:
            booking.meeting_link = meet_link
            booking.calendar_event_id = event_id
            update_fields += ["meeting_link", "calendar_event_id"]
        booking.save(update_fields=update_fields)

        notify_booking_payment_confirmed_task.delay(booking.pk)
