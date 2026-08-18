import hashlib
import hmac
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.specialists.models import Specialist

from . import paymob
from .models import Order, Payment
from .services import create_order_for_item

User = get_user_model()

PAYMOB_TEST_SETTINGS = {
    "PAYMOB_HMAC_SECRET": "test-hmac-secret",
}

PAYMOB_CONFIGURED_SETTINGS = {
    "PAYMOB_API_KEY": "test-api-key",
    "PAYMOB_INTEGRATION_ID": "12345",
    "PAYMOB_IFRAME_ID": "67890",
    "PAYMOB_HMAC_SECRET": "test-hmac-secret",
}


def _sign(transaction_data, secret):
    concatenated = "".join(
        paymob._stringify(paymob._get_nested(transaction_data, field))
        for field in paymob._HMAC_FIELDS
    )
    return hmac.new(secret.encode(), concatenated.encode(), hashlib.sha512).hexdigest()


def _transaction_data(**overrides):
    data = {
        "amount_cents": "20000",
        "created_at": "2026-01-01T00:00:00.000000",
        "currency": "EGP",
        "error_occured": False,
        "has_parent_transaction": False,
        "id": 999888,
        "integration_id": 12345,
        "is_3d_secure": True,
        "is_auth": False,
        "is_capture": False,
        "is_refunded": False,
        "is_standalone_payment": True,
        "is_voided": False,
        "order": {"id": 555444},
        "owner": 1,
        "pending": False,
        "source_data": {"pan": "1234", "sub_type": "Visa", "type": "card"},
        "success": True,
    }
    data.update(overrides)
    return data


class PaymobWebhookTests(TestCase):
    def setUp(self):
        self.webhook_url = reverse("paymob-webhook")
        self.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="whatever-123"
        )
        specialist_user = User.objects.create_user(
            username="webhookspecialist",
            email="webhookspecialist@example.com",
            password="whatever-123",
        )
        self.specialist = Specialist.objects.create(
            user=specialist_user, status="approved", full_name_ar="د. ليلى", hourly_rate=200
        )
        self.order = create_order_for_item(self.user, self.specialist, Decimal("200.00"))
        self.payment = Payment.objects.create(
            order=self.order,
            method="card",
            status="initiated",
            provider_reference="555444",
        )

    def _post(self, transaction_data, hmac_value):
        return self.client.post(
            f"{self.webhook_url}?hmac={hmac_value}",
            data=json.dumps({"obj": transaction_data}),
            content_type="application/json",
        )

    @override_settings(**PAYMOB_TEST_SETTINGS)
    def test_valid_signature_accepted_and_marks_payment_succeeded(self):
        transaction_data = _transaction_data(order={"id": 555444}, success=True)
        signature = _sign(transaction_data, "test-hmac-secret")

        response = self._post(transaction_data, signature)

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, "succeeded")
        self.assertEqual(self.order.status, "paid")
        self.assertTrue(hasattr(self.order, "invoice"))
        self.assertTrue(self.order.invoice.pdf_file.name)

    @override_settings(**PAYMOB_TEST_SETTINGS)
    def test_invalid_signature_rejected_with_403(self):
        transaction_data = _transaction_data(order={"id": 555444}, success=True)

        response = self._post(transaction_data, "0" * 128)

        self.assertEqual(response.status_code, 403)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "initiated")

    @override_settings(**PAYMOB_TEST_SETTINGS)
    def test_missing_signature_rejected_with_403(self):
        transaction_data = _transaction_data(order={"id": 555444}, success=True)

        response = self.client.post(
            self.webhook_url,
            data=json.dumps({"obj": transaction_data}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "initiated")

    @override_settings(PAYMOB_HMAC_SECRET="")
    def test_no_hmac_secret_configured_rejects_everything(self):
        transaction_data = _transaction_data(order={"id": 555444}, success=True)
        # Even a signature computed with *some* secret can't pass — there's
        # no configured secret to validate against at all.
        signature = _sign(transaction_data, "whatever")

        response = self._post(transaction_data, signature)

        self.assertEqual(response.status_code, 403)

    @override_settings(**PAYMOB_TEST_SETTINGS)
    def test_malformed_json_body_returns_403_not_500(self):
        response = self.client.post(
            f"{self.webhook_url}?hmac=irrelevant",
            data="not-json-at-all{{{",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(**PAYMOB_TEST_SETTINGS)
    def test_no_matching_payment_acks_200_without_crashing(self):
        transaction_data = _transaction_data(order={"id": 999999999}, success=True)
        signature = _sign(transaction_data, "test-hmac-secret")

        response = self._post(transaction_data, signature)

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "initiated")

    @override_settings(**PAYMOB_TEST_SETTINGS)
    def test_failed_transaction_marks_payment_failed(self):
        transaction_data = _transaction_data(
            order={"id": 555444}, success=False, data={"message": "Insufficient funds"}
        )
        signature = _sign(transaction_data, "test-hmac-secret")

        response = self._post(transaction_data, signature)

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, "failed")
        self.assertEqual(self.order.status, "pending")


class CardPaymentAvailabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="checkoutuser", email="checkoutuser@example.com", password="whatever-123"
        )
        specialist_user = User.objects.create_user(
            username="checkoutspecialist",
            email="checkoutspecialist@example.com",
            password="whatever-123",
        )
        specialist = Specialist.objects.create(
            user=specialist_user, status="approved", full_name_ar="د. عمر", hourly_rate=150
        )
        self.order = create_order_for_item(self.user, specialist, Decimal("150.00"))
        self.checkout_url = reverse("payments:checkout", kwargs={"order_id": self.order.pk})
        self.client.force_login(self.user)

    @override_settings(PAYMOB_API_KEY="", PAYMOB_INTEGRATION_ID="", PAYMOB_IFRAME_ID="")
    def test_card_option_marked_unavailable_without_paymob_keys(self):
        response = self.client.get(self.checkout_url)
        self.assertFalse(response.context["card_available"])

    @override_settings(PAYMOB_API_KEY="", PAYMOB_INTEGRATION_ID="", PAYMOB_IFRAME_ID="")
    def test_card_payment_attempt_blocked_without_paymob_keys(self):
        response = self.client.post(self.checkout_url, data={"method": "card"})
        # Re-renders the checkout form rather than redirecting anywhere
        # that would imply a payment attempt started.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 0)
        messages = list(response.context["messages"])
        self.assertTrue(
            any("الدفع بالبطاقة غير مُفعّل حاليًا" in str(m) for m in messages),
            "expected an error message on the response context",
        )

    @override_settings(**PAYMOB_CONFIGURED_SETTINGS)
    def test_card_option_marked_available_with_paymob_keys(self):
        response = self.client.get(self.checkout_url)
        self.assertTrue(response.context["card_available"])

    def test_bank_transfer_always_available(self):
        response = self.client.post(self.checkout_url, data={"method": "bank_transfer"})
        self.assertRedirects(
            response, reverse("payments:bank-transfer-pending", kwargs={"order_id": self.order.pk})
        )
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.method, "bank_transfer")
        self.assertEqual(payment.status, "initiated")


class OrderTotalsTests(TestCase):
    def test_vat_is_computed_at_14_percent(self):
        user = User.objects.create_user(
            username="vatuser", email="vatuser@example.com", password="whatever-123"
        )
        specialist_user = User.objects.create_user(
            username="vatspecialist", email="vatspecialist@example.com", password="whatever-123"
        )
        specialist = Specialist.objects.create(
            user=specialist_user, status="approved", full_name_ar="د. هدى", hourly_rate=100
        )
        order = create_order_for_item(user, specialist, Decimal("100.00"))
        self.assertEqual(order.subtotal, Decimal("100.00"))
        self.assertEqual(order.vat_amount, Decimal("14.00"))
        self.assertEqual(order.total, Decimal("114.00"))
        self.assertIsInstance(order, Order)
