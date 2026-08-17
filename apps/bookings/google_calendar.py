"""Creates a Google Calendar event (with an auto-generated Google Meet
link) for each booking, authenticated as a real Google account (OAuth
refresh token) rather than a service account — Google Meet auto-creation
via the Calendar API isn't available to plain service accounts (confirmed
against the live API: "Invalid conference type value"). Run
`python manage.py google_calendar_authorize` once to obtain
GOOGLE_CALENDAR_REFRESH_TOKEN — see apps/bookings/management/commands/ and
docs/google-calendar-setup.md. Degrades gracefully everywhere: unset
credentials or any Calendar API error just means no meeting_link — the
booking itself still succeeds either way."""

import logging
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _get_service():
    if not (
        settings.GOOGLE_CALENDAR_CLIENT_ID
        and settings.GOOGLE_CALENDAR_CLIENT_SECRET
        and settings.GOOGLE_CALENDAR_REFRESH_TOKEN
    ):
        return None

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(
        token=None,
        refresh_token=settings.GOOGLE_CALENDAR_REFRESH_TOKEN,
        token_uri=TOKEN_URI,
        client_id=settings.GOOGLE_CALENDAR_CLIENT_ID,
        client_secret=settings.GOOGLE_CALENDAR_CLIENT_SECRET,
        scopes=CALENDAR_SCOPES,
    )
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def _extract_meet_link(event):
    for entry_point in event.get("conferenceData", {}).get("entryPoints", []):
        if entry_point.get("entryPointType") == "video":
            return entry_point.get("uri")
    return None


def create_meeting_for_booking(booking):
    """Returns (meet_link, calendar_event_id), or (None, None) if Calendar
    isn't configured or the API call fails."""
    service = _get_service()
    if service is None:
        return None, None

    event_body = {
        "summary": f"جلسة مع {booking.specialist.full_name_ar or booking.specialist.full_name_en}",
        "description": booking.notes or "",
        "start": {"dateTime": booking.scheduled_start.isoformat()},
        "end": {"dateTime": booking.scheduled_end.isoformat()},
        "attendees": [{"email": booking.client.email}, {"email": booking.specialist.user.email}],
        "conferenceData": {
            "createRequest": {
                "requestId": f"booking-{booking.pk}-{uuid.uuid4().hex[:8]}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    try:
        event = (
            service.events()
            .insert(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                body=event_body,
                conferenceDataVersion=1,
                # A plain service account (no Workspace domain-wide delegation)
                # can't send invite emails on attendees' behalf — we email our
                # own confirmation separately (apps.notifications) anyway.
                sendUpdates="none",
            )
            .execute()
        )
    except Exception:
        logger.exception("Failed to create Google Calendar event for booking %s", booking.pk)
        return None, None

    meet_link = event.get("hangoutLink") or _extract_meet_link(event)
    return meet_link, event.get("id")


def delete_event(event_id):
    service = _get_service()
    if service is None or not event_id:
        return
    try:
        service.events().delete(
            calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id, sendUpdates="none"
        ).execute()
    except Exception:
        logger.exception("Failed to delete Google Calendar event %s", event_id)
