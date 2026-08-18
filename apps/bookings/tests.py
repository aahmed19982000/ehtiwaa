from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.specialists.models import Specialist

from . import google_calendar
from .models import Availability, Booking

User = get_user_model()


class BookingCreateViewTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client1", email="client1@example.com", password="whatever-123"
        )
        specialist_user = User.objects.create_user(
            username="specialist1", email="specialist1@example.com", password="whatever-123"
        )
        self.specialist = Specialist.objects.create(
            user=specialist_user,
            status="approved",
            full_name_ar="د. سارة",
            full_name_en="Dr. Sara",
            hourly_rate=200,
        )
        # A couple of days out, well clear of "now" regardless of when the
        # test runs, and using specific_date (not weekday) so it's not
        # sensitive to which day of the week the suite happens to run on.
        self.target_date = timezone.localdate() + timedelta(days=2)
        Availability.objects.create(
            specialist=self.specialist,
            specific_date=self.target_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_active=True,
        )
        self.slot_value = f"{self.target_date.isoformat()}T09:00"
        self.create_url = reverse("bookings:create", kwargs={"specialist_pk": self.specialist.pk})

    def _post_booking(self):
        return self.client.post(
            self.create_url,
            data={
                "date": self.target_date.isoformat(),
                "time_slot": self.slot_value,
                "contact_phone": "01001234567",
                "notes": "أول جلسة",
            },
        )

    def test_anonymous_user_cannot_book(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        response = self._post_booking()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertEqual(Booking.objects.count(), 0)

    @patch("apps.bookings.views.notify_booking_created_task")
    def test_successful_booking_redirects_to_checkout(self, mock_notify_task):
        self.client.force_login(self.client_user)
        response = self._post_booking()

        booking = Booking.objects.get(client=self.client_user, specialist=self.specialist)
        self.assertEqual(booking.status, "pending")
        self.assertEqual(booking.contact_phone, "01001234567")
        self.assertRedirects(
            response,
            reverse("payments:checkout", kwargs={"order_id": self._get_order_id(response)}),
        )
        mock_notify_task.delay.assert_called_once_with(booking.pk)

    def _get_order_id(self, response):
        # The redirect target itself encodes the order id — pull it back out
        # instead of hard-coding an assumption about which id gets assigned.
        from apps.payments.models import Order

        return Order.objects.get(user=self.client_user).pk

    @patch("apps.bookings.views.notify_booking_created_task")
    def test_double_booking_same_slot_prevented(self, mock_notify_task):
        self.client.force_login(self.client_user)
        first_response = self._post_booking()
        self.assertEqual(Booking.objects.count(), 1)

        other_client = User.objects.create_user(
            username="client2", email="client2@example.com", password="whatever-123"
        )
        self.client.force_login(other_client)
        second_response = self._post_booking()

        # The slot is no longer offered at all (it's already taken), so the
        # second submission is rejected — either as a stale/invalid choice
        # or the explicit race-condition message — but must not create a
        # second Booking for the same specialist/slot.
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(
            Booking.objects.filter(
                specialist=self.specialist, scheduled_start__date=self.target_date
            ).count(),
            1,
        )
        self.assertNotEqual(first_response.status_code, second_response.status_code)


class GoogleCalendarMissingConfigTests(TestCase):
    """GOOGLE_CALENDAR_CLIENT_ID/SECRET/REFRESH_TOKEN are blank by default in
    every local/test environment (see .env.example) — the whole point of
    apps.bookings.google_calendar is to degrade gracefully rather than
    crash a booking when they're unset."""

    @override_settings(
        GOOGLE_CALENDAR_CLIENT_ID="",
        GOOGLE_CALENDAR_CLIENT_SECRET="",
        GOOGLE_CALENDAR_REFRESH_TOKEN="",
    )
    def test_create_meeting_returns_none_without_crashing(self):
        client_user = User.objects.create_user(
            username="calclient", email="calclient@example.com", password="whatever-123"
        )
        specialist_user = User.objects.create_user(
            username="calspecialist", email="calspecialist@example.com", password="whatever-123"
        )
        specialist = Specialist.objects.create(
            user=specialist_user,
            status="approved",
            full_name_ar="د. منى",
            full_name_en="Dr. Mona",
            hourly_rate=150,
        )
        start = timezone.now() + timedelta(days=1)
        booking = Booking.objects.create(
            client=client_user,
            specialist=specialist,
            status="pending",
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=1),
        )

        meet_link, event_id = google_calendar.create_meeting_for_booking(booking)

        self.assertIsNone(meet_link)
        self.assertIsNone(event_id)

    @override_settings(
        GOOGLE_CALENDAR_CLIENT_ID="",
        GOOGLE_CALENDAR_CLIENT_SECRET="",
        GOOGLE_CALENDAR_REFRESH_TOKEN="",
    )
    def test_delete_event_does_not_crash_without_config(self):
        # Must not raise even when passed a (fake) event id — there's simply
        # no configured service to call.
        google_calendar.delete_event("some-fake-event-id")
