import zoneinfo

from django.utils import timezone

TIMEZONE_COOKIE_NAME = "client_tz"


class ClientTimezoneMiddleware:
    """Activates the requesting browser's own IANA timezone — detected
    client-side (see the inline script in templates/base.html) and sent
    back as a cookie — for this request's rendering only. Stored datetimes
    are untouched; this only changes how aware datetimes display (booking
    times, "member since", etc.) via Django's normal timezone-aware
    template filters."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = request.COOKIES.get(TIMEZONE_COOKIE_NAME)
        if tz_name:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tz_name))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError):
                timezone.deactivate()
        else:
            timezone.deactivate()
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
