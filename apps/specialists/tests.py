from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import MIN_EXPERIENCE_YEARS, SpecialistApplicationForm, SpecialistDocumentsForm
from .models import CredentialDocument, Specialist

User = get_user_model()

AUTH0_TEST_SETTINGS = {
    "AUTH0_DOMAIN": "test.auth0.example.com",
    "AUTH0_CLIENT_ID": "test-client-id",
    "AUTH0_CLIENT_SECRET": "test-client-secret",
    "SOCIALACCOUNT_PROVIDERS": {
        "google": {"APPS": []},
        "auth0": {
            "AUTH0_URL": "https://test.auth0.example.com",
            "APPS": [{"client_id": "test-client-id", "secret": "test-client-secret", "key": ""}],
        },
    },
}


def _pdf_bytes(size=1024):
    return b"%PDF-1.4\n" + (b"0" * size)


class SpecialistApplicationFormTests(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "category": "psychiatrist",
            "full_name_ar": "أحمد محمد",
            "full_name_en": "Ahmed Mohamed",
            "title": "dr",
            "country_code": "+20",
            "phone": "1001234567",
            "birth_year": 1985,
            "gender": "male",
            "nationality": "EG",
            "country_of_residence": "EG",
            "languages": ["ar", "en"],
            "agree_terms": True,
            "email": "specialist@example.com",
            "password1": "a-strong-password-1",
            "password2": "a-strong-password-1",
        }
        data.update(overrides)
        return data

    def test_psychiatrist_does_not_require_minimum_experience(self):
        form = SpecialistApplicationForm(data=self._valid_data(category="psychiatrist"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_counselor_below_minimum_experience_rejected(self):
        form = SpecialistApplicationForm(
            data=self._valid_data(
                category="counselor", years_of_experience=MIN_EXPERIENCE_YEARS - 1
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("years_of_experience", form.errors)

    def test_counselor_missing_experience_rejected(self):
        form = SpecialistApplicationForm(data=self._valid_data(category="counselor"))
        self.assertFalse(form.is_valid())
        self.assertIn("years_of_experience", form.errors)

    def test_clinical_psychologist_meets_minimum_experience_passes(self):
        form = SpecialistApplicationForm(
            data=self._valid_data(
                category="clinical_psychologist", years_of_experience=MIN_EXPERIENCE_YEARS
            )
        )
        self.assertTrue(form.is_valid(), form.errors)


class SpecialistDocumentsFormTests(TestCase):
    def test_required_documents_enforced_for_category(self):
        # psychiatrist requires 4 documents (see CATEGORY_DOCUMENTS) — submit none.
        form = SpecialistDocumentsForm(data={}, category="psychiatrist")
        self.assertFalse(form.is_valid())
        self.assertIn("degree_certificate", form.errors)
        self.assertIn("license_file", form.errors)
        self.assertIn("syndicate_card", form.errors)
        self.assertIn("postgraduate_certificate", form.errors)

    def test_only_relevant_fields_rendered_for_category(self):
        form = SpecialistDocumentsForm(category="clinical_psychologist")
        self.assertIn("degree_certificate", form.fields)
        self.assertIn("supervision_proof", form.fields)
        self.assertNotIn("license_file", form.fields)
        self.assertNotIn("syndicate_card", form.fields)

    def test_bad_extension_rejected(self):
        malicious = SimpleUploadedFile(
            "certificate.exe", b"MZ-fake-binary-content", content_type="application/octet-stream"
        )
        form = SpecialistDocumentsForm(
            data={},
            files={"degree_certificate": malicious},
            category="clinical_psychologist",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("degree_certificate", form.errors)
        self.assertIn("نوع الملف غير مدعوم", str(form.errors["degree_certificate"]))

    def test_script_content_disguised_with_allowed_extension_rejected(self):
        # A real-world variant of the extension-bypass QA finding: renaming
        # a script to a document extension passes
        # FileExtensionAllowlistValidator (it only reads the filename) —
        # FileContentValidator is what actually catches this, by checking
        # the file's leading bytes don't start with "%PDF-".
        disguised_script = SimpleUploadedFile(
            "certificate.pdf", b"#!/bin/sh\nrm -rf /\n", content_type="application/pdf"
        )
        form = SpecialistDocumentsForm(
            data={},
            files={"degree_certificate": disguised_script},
            category="clinical_psychologist",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("محتوى الملف لا يطابق نوعه المعلن", str(form.errors["degree_certificate"]))

    def test_oversized_document_rejected(self):
        # DOCUMENT_MAX_SIZE_MB is 10 in apps/core/validators.py.
        big_file = SimpleUploadedFile(
            "certificate.pdf", _pdf_bytes(size=11 * 1024 * 1024), content_type="application/pdf"
        )
        form = SpecialistDocumentsForm(
            data={},
            files={"degree_certificate": big_file},
            category="clinical_psychologist",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("حجم الملف كبير جدًا", str(form.errors["degree_certificate"]))

    def test_valid_documents_accepted(self):
        good_file = SimpleUploadedFile(
            "certificate.pdf", _pdf_bytes(), content_type="application/pdf"
        )
        proof_file = SimpleUploadedFile("proof.pdf", _pdf_bytes(), content_type="application/pdf")
        form = SpecialistDocumentsForm(
            data={},
            files={"degree_certificate": good_file, "supervision_proof": proof_file},
            category="clinical_psychologist",
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.documents()), 2)


class SpecialistApplyFlowTests(TestCase):
    """End-to-end application flow: anonymous applicant -> account created
    via (mocked) Auth0 -> Specialist row -> credential documents."""

    def setUp(self):
        self.apply_url = reverse("specialists:apply")
        self.documents_url = reverse("specialists:apply-documents")

    @patch("apps.accounts.auth0.get_userinfo")
    @patch("apps.accounts.auth0.login")
    @patch("apps.accounts.auth0.signup")
    def test_full_application_creates_specialist_and_documents(
        self, mock_signup, mock_login, mock_userinfo
    ):
        mock_signup.return_value = {"_id": "auth0|new-specialist"}
        mock_login.return_value = {"access_token": "fake-token"}
        mock_userinfo.return_value = {
            "sub": "auth0|new-specialist",
            "email": "newspecialist@example.com",
            "email_verified": True,
            "name": "Ahmed Mohamed",
        }

        with override_settings(**AUTH0_TEST_SETTINGS):
            response = self.client.post(
                self.apply_url,
                data={
                    "category": "clinical_psychologist",
                    "full_name_ar": "أحمد محمد",
                    "full_name_en": "Ahmed Mohamed",
                    "title": "dr",
                    "country_code": "+20",
                    "phone": "1001234567",
                    "birth_year": 1985,
                    "gender": "male",
                    "nationality": "EG",
                    "country_of_residence": "EG",
                    "languages": ["ar", "en"],
                    "years_of_experience": 6,
                    "agree_terms": True,
                    "email": "newspecialist@example.com",
                    "password1": "a-strong-password-1",
                    "password2": "a-strong-password-1",
                },
            )
        self.assertRedirects(response, self.documents_url)

        user = User.objects.get(email="newspecialist@example.com")
        specialist = Specialist.objects.get(user=user)
        self.assertEqual(specialist.status, "pending")
        self.assertEqual(specialist.category, "clinical_psychologist")
        self.assertEqual(user.role, "specialist")

        degree_file = SimpleUploadedFile("degree.pdf", _pdf_bytes(), content_type="application/pdf")
        proof_file = SimpleUploadedFile("proof.pdf", _pdf_bytes(), content_type="application/pdf")
        doc_response = self.client.post(
            self.documents_url,
            data={"degree_certificate": degree_file, "supervision_proof": proof_file},
        )
        self.assertRedirects(doc_response, reverse("specialists:apply-pending"))
        self.assertEqual(CredentialDocument.objects.filter(specialist=specialist).count(), 2)

    def test_documents_step_requires_login(self):
        response = self.client.get(self.documents_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_documents_step_blocked_without_application(self):
        user = User.objects.create_user(
            username="noapp", email="noapp@example.com", password="whatever-123"
        )
        self.client.force_login(user)
        response = self.client.get(self.documents_url)
        self.assertRedirects(response, self.apply_url)

    @patch("apps.accounts.auth0.signup")
    def test_below_min_experience_never_reaches_auth0(self, mock_signup):
        with override_settings(**AUTH0_TEST_SETTINGS):
            response = self.client.post(
                self.apply_url,
                data={
                    "category": "counselor",
                    "full_name_ar": "أحمد محمد",
                    "full_name_en": "Ahmed Mohamed",
                    "title": "dr",
                    "country_code": "+20",
                    "phone": "1001234568",
                    "birth_year": 1985,
                    "gender": "male",
                    "nationality": "EG",
                    "country_of_residence": "EG",
                    "languages": ["ar"],
                    "years_of_experience": 1,
                    "agree_terms": True,
                    "email": "rejected@example.com",
                    "password1": "a-strong-password-1",
                    "password2": "a-strong-password-1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, f"مطلوب {MIN_EXPERIENCE_YEARS} سنوات خبرة على الأقل لهذه الفئة."
        )
        mock_signup.assert_not_called()
        self.assertFalse(User.objects.filter(email="rejected@example.com").exists())


class SpecialistDirectoryFilterTests(TestCase):
    def setUp(self):
        def make_specialist(username, **kwargs):
            user = User.objects.create_user(
                username=username, email=f"{username}@example.com", password="whatever-123"
            )
            defaults = {
                "status": "approved",
                "category": "psychiatrist",
                "gender": "male",
                "hourly_rate": 100,
                "languages": ["ar"],
            }
            defaults.update(kwargs)
            return Specialist.objects.create(user=user, **defaults)

        self.psychiatrist = make_specialist(
            "psych1", category="psychiatrist", hourly_rate=300, gender="male", languages=["ar"]
        )
        self.counselor = make_specialist(
            "counselor1",
            category="counselor",
            hourly_rate=100,
            gender="female",
            languages=["en"],
        )
        self.pending_specialist = make_specialist(
            "pending1", category="psychiatrist", status="pending", hourly_rate=50
        )
        self.directory_url = reverse("specialists:directory")

    def test_pending_specialists_excluded(self):
        response = self.client.get(self.directory_url)
        specialists = list(response.context["specialists"])
        self.assertNotIn(self.pending_specialist, specialists)
        self.assertEqual(len(specialists), 2)

    def test_filter_by_category(self):
        response = self.client.get(self.directory_url, {"category": "counselor"})
        specialists = list(response.context["specialists"])
        self.assertEqual(specialists, [self.counselor])

    def test_filter_by_gender(self):
        response = self.client.get(self.directory_url, {"gender": "female"})
        specialists = list(response.context["specialists"])
        self.assertEqual(specialists, [self.counselor])

    def test_filter_by_price_range(self):
        response = self.client.get(self.directory_url, {"price_min": 200, "price_max": 400})
        specialists = list(response.context["specialists"])
        self.assertEqual(specialists, [self.psychiatrist])

    def test_sort_by_price_ascending(self):
        response = self.client.get(self.directory_url, {"sort": "price_asc"})
        specialists = list(response.context["specialists"])
        self.assertEqual(specialists, [self.counselor, self.psychiatrist])

    def test_invalid_price_range_shows_form_error(self):
        response = self.client.get(self.directory_url, {"price_min": 500, "price_max": 100})
        self.assertIn("price_max", response.context["filter_form"].errors)
