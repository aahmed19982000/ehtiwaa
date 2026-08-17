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
