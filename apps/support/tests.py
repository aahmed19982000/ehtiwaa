from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import SupportTicket

User = get_user_model()


class TicketOwnershipTests(TestCase):
    """apps.support has no user-facing "view/edit my ticket" page at all
    (see apps/support/urls.py — creation only, everything else is
    Django admin/staff-only), so there's no direct IDOR surface of the
    "user A edits user B's ticket" shape to exercise here. The closest
    real equivalent is: a ticket's `user` FK must always come from
    request.user, and must never be attributable to someone else via
    form/POST data (TicketForm has no `user` field at all, but this
    confirms it end-to-end through the actual view)."""

    def setUp(self):
        self.url = reverse("support:ticket-create")
        self.owner = User.objects.create_user(
            username="ticketowner", email="ticketowner@example.com", password="whatever-123"
        )
        self.other_user = User.objects.create_user(
            username="notowner", email="notowner@example.com", password="whatever-123"
        )

    def _post(self, **extra):
        data = {
            "full_name": "Test User",
            "email": "ticketowner@example.com",
            "subject": "مشكلة في الدفع",
            "body": "تفاصيل المشكلة هنا.",
        }
        data.update(extra)
        return self.client.post(self.url, data=data)

    def test_authenticated_submission_is_attributed_to_requester(self):
        self.client.force_login(self.owner)
        self._post()
        ticket = SupportTicket.objects.get(subject="مشكلة في الدفع")
        self.assertEqual(ticket.user, self.owner)

    def test_user_field_cannot_be_spoofed_via_post_data(self):
        self.client.force_login(self.owner)
        # TicketForm doesn't expose a "user" field at all — confirm the
        # view ignores any such POST data rather than trusting it.
        self._post(user=self.other_user.pk, user_id=self.other_user.pk)
        ticket = SupportTicket.objects.get(subject="مشكلة في الدفع")
        self.assertEqual(ticket.user, self.owner)
        self.assertNotEqual(ticket.user, self.other_user)

    def test_anonymous_submission_has_no_user(self):
        self._post()
        ticket = SupportTicket.objects.get(subject="مشكلة في الدفع")
        self.assertIsNone(ticket.user)
