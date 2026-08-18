from collections import defaultdict
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


def _windows_for_day(windows, target_date):
    specific = [w for w in windows if w.specific_date == target_date]
    if specific:
        return specific
    return [w for w in windows if w.specific_date is None and w.weekday == target_date.weekday()]


def _earliest_free_slot_on_day(windows, target_date, duration, booked_ranges, now):
    day_windows = sorted(_windows_for_day(windows, target_date), key=lambda w: w.start_time)
    for window in day_windows:
        current = timezone.make_aware(datetime.combine(target_date, window.start_time))
        window_end = timezone.make_aware(datetime.combine(target_date, window.end_time))
        while current + duration <= window_end:
            slot_end = current + duration
            if current > now:
                is_booked = any(
                    current < b_end and slot_end > b_start for b_start, b_end in booked_ranges
                )
                if not is_booked:
                    return current
            current += duration
    return None


def get_next_available_slots(specialists, lookahead_days=SLOT_LOOKAHEAD_DAYS):
    """Bulk-computes the earliest free slot (if any, within the next
    `lookahead_days`) for every specialist in `specialists` — two queries
    for the whole list rather than looking up each specialist's
    availability/bookings one at a time, since this feeds the directory
    listing page (apps.specialists.views.SpecialistDirectoryView), not a
    single specialist's booking page.

    Returns {specialist_id: datetime | None}.
    """
    specialists = list(specialists)
    specialist_ids = [s.pk for s in specialists]
    if not specialist_ids:
        return {}

    now = timezone.now()
    today = timezone.localdate()
    horizon = today + timedelta(days=lookahead_days)

    windows_by_specialist = defaultdict(list)
    for window in Availability.objects.filter(specialist_id__in=specialist_ids, is_active=True):
        windows_by_specialist[window.specialist_id].append(window)

    booked_by_specialist = defaultdict(list)
    for specialist_id, start, end in Booking.objects.filter(
        specialist_id__in=specialist_ids,
        status__in=["pending", "confirmed"],
        scheduled_start__date__gte=today,
        scheduled_start__date__lte=horizon,
    ).values_list("specialist_id", "scheduled_start", "scheduled_end"):
        booked_by_specialist[specialist_id].append((start, end))

    results = {}
    for specialist in specialists:
        windows = windows_by_specialist.get(specialist.pk)
        if not windows:
            results[specialist.pk] = None
            continue
        duration = timedelta(minutes=get_session_duration_minutes(specialist))
        booked_ranges = booked_by_specialist.get(specialist.pk, [])
        next_slot = None
        for offset in range(lookahead_days + 1):
            day = today + timedelta(days=offset)
            next_slot = _earliest_free_slot_on_day(windows, day, duration, booked_ranges, now)
            if next_slot:
                break
        results[specialist.pk] = next_slot
    return results


def confirm_bookings_from_paid_order(order):
    """Moves every still-pending Booking in this paid Order to confirmed —
    called from apps.payments.services.handle_payment_succeeded. The
    Google Meet link is deliberately created here, not at booking-request
    time: generating a calendar invite for a session nobody has paid for
    yet would clutter the specialist's calendar with sessions that may
    never happen."""
    from apps.core.tasks import safe_delay
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

        safe_delay(notify_booking_payment_confirmed_task, booking.pk)
