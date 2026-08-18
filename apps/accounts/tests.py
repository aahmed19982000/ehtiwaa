from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .auth0 import Auth0Error
from .forms import SignupForm
from .models import Profile

User = get_user_model()

# Enables the Auth0-backed signup/login views (they redirect to "welcome"
# with an error otherwise — see apps.accounts.views._social_provider_flags).
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


def _tiny_png_bytes(padding=0):
    buf = BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format="PNG")
    return buf.getvalue() + b"\0" * padding


def _tiny_gif_bytes():
    buf = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(buf, format="GIF")
    return buf.getvalue()


class SignupFormTests(TestCase):
    """Pure form-level validation — no Auth0/network involved."""

    def _valid_data(self, **overrides):
        data = {
            "full_name": "Sara Ahmed",
            "email": "sara@example.com",
            "country_code": "+20",
            "phone": "1001234567",
            "password1": "a-strong-password-1",
            "password2": "a-strong-password-1",
            "agree_terms": True,
        }
        data.update(overrides)
        return data

    def test_valid_data_passes(self):
        form = SignupForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(
            username="existing", email="sara@example.com", password="whatever-123"
        )
        form = SignupForm(data=self._valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_email_is_case_insensitive(self):
        User.objects.create_user(
            username="existing", email="Sara@Example.com", password="whatever-123"
        )
        form = SignupForm(data=self._valid_data(email="sara@example.com"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_mismatch_rejected(self):
        form = SignupForm(data=self._valid_data(password2="different-password-1"))
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class SignupViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:signup")

    def test_get_redirects_when_auth0_not_configured(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("accounts:welcome"))

    def test_post_duplicate_email_does_not_call_auth0(self):
        User.objects.create_user(
            username="existing", email="sara@example.com", password="whatever-123"
        )
        with override_settings(**AUTH0_TEST_SETTINGS), patch(
            "apps.accounts.auth0.signup"
        ) as mock_signup:
            response = self.client.post(
                self.url,
                data={
                    "full_name": "Sara Ahmed",
                    "email": "sara@example.com",
                    "country_code": "+20",
                    "phone": "1001234567",
                    "password1": "a-strong-password-1",
                    "password2": "a-strong-password-1",
                    "agree_terms": True,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هذا البريد الإلكتروني مستخدم بالفعل.")
        mock_signup.assert_not_called()
        self.assertEqual(User.objects.filter(email="sara@example.com").count(), 1)

    @patch("apps.accounts.auth0.get_userinfo")
    @patch("apps.accounts.auth0.login")
    @patch("apps.accounts.auth0.signup")
    def test_post_success_creates_user_and_logs_in(self, mock_signup, mock_login, mock_userinfo):
        mock_signup.return_value = {"_id": "auth0|abc123"}
        mock_login.return_value = {"access_token": "fake-token"}
        mock_userinfo.return_value = {
            "sub": "auth0|abc123",
            "email": "new-user@example.com",
            "email_verified": True,
            "name": "New User",
        }

        with override_settings(**AUTH0_TEST_SETTINGS):
            response = self.client.post(
                self.url,
                data={
                    "full_name": "New User",
                    "email": "new-user@example.com",
                    "country_code": "+20",
                    "phone": "1009876543",
                    "password1": "a-strong-password-1",
                    "password2": "a-strong-password-1",
                    "agree_terms": True,
                },
            )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new-user@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        self.assertEqual(user.phone, "+201009876543")
        self.assertFalse(user.has_usable_password())
        mock_signup.assert_called_once()
        mock_login.assert_called_once()

    @patch("apps.accounts.auth0.signup")
    def test_post_auth0_error_shows_message_and_does_not_create_user(self, mock_signup):
        mock_signup.side_effect = Auth0Error("هذا البريد الإلكتروني مسجّل بحساب موجود بالفعل.")

        with override_settings(**AUTH0_TEST_SETTINGS):
            response = self.client.post(
                self.url,
                data={
                    "full_name": "New User",
                    "email": "brand-new@example.com",
                    "country_code": "+20",
                    "phone": "1009876543",
                    "password1": "a-strong-password-1",
                    "password2": "a-strong-password-1",
                    "agree_terms": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هذا البريد الإلكتروني مسجّل بحساب موجود بالفعل.")
        self.assertFalse(User.objects.filter(email="brand-new@example.com").exists())


class LoginViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:login")

    def test_get_redirects_when_auth0_not_configured(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("accounts:welcome"))

    @patch("apps.accounts.auth0.get_userinfo")
    @patch("apps.accounts.auth0.login")
    def test_post_correct_credentials_logs_in(self, mock_login, mock_userinfo):
        mock_login.return_value = {"access_token": "fake-token"}
        mock_userinfo.return_value = {
            "sub": "auth0|existing-user",
            "email": "existing@example.com",
            "email_verified": True,
            "name": "Existing User",
        }

        with override_settings(**AUTH0_TEST_SETTINGS):
            response = self.client.post(
                self.url, data={"email": "existing@example.com", "password": "correct-password"}
            )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="existing@example.com")
        self.assertTrue(user.is_active)
        mock_login.assert_called_once_with(
            email="existing@example.com", password="correct-password"
        )

    @patch("apps.accounts.auth0.login")
    def test_post_incorrect_credentials_rejected(self, mock_login):
        mock_login.side_effect = Auth0Error("البريد الإلكتروني أو كلمة المرور غير صحيحة.")

        with override_settings(**AUTH0_TEST_SETTINGS):
            response = self.client.post(
                self.url, data={"email": "someone@example.com", "password": "wrong-password"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "البريد الإلكتروني أو كلمة المرور غير صحيحة.")
        self.assertFalse(User.objects.filter(email="someone@example.com").exists())


class ProfileEditViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:profile")
        self.user = User.objects.create_user(
            username="profileuser", email="profile@example.com", password="whatever-123"
        )
        self.profile = Profile.objects.create(user=self.user)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_valid_update_saves_profile_and_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "profile@example.com",
                "phone": "",
                "bio": "Hello there.",
                "city": "Cairo",
            },
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.profile.bio, "Hello there.")
        self.assertEqual(self.profile.city, "Cairo")

    def test_exe_file_rejected_as_avatar(self):
        self.client.force_login(self.user)
        # Real (valid) PNG bytes so Django's built-in ImageField content
        # check doesn't reject it for being corrupt — Django's own
        # `validate_image_file_extension` is what actually blocks ".exe"
        # here, since "exe" isn't a Pillow-recognized extension. See
        # test_gif_rejected_as_avatar below for a case that isolates *our*
        # allowlist validator (apps/core/validators.py) specifically.
        malicious = SimpleUploadedFile("avatar.exe", _tiny_png_bytes(), content_type="image/png")
        response = self.client.post(
            self.url,
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "profile@example.com",
                "phone": "",
                "bio": "",
                "city": "",
                "avatar": malicious,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["profile_form"].errors.get("avatar"))
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.avatar)

    def test_gif_rejected_as_avatar(self):
        """A real, valid GIF is accepted by Django's own built-in
        ImageField extension check (Pillow supports GIF) — so this is the
        case that specifically isolates our own extension allowlist
        (IMAGE_EXTENSIONS in apps/core/validators.py only allows
        jpg/jpeg/png/webp, not gif)."""
        self.client.force_login(self.user)
        gif_file = SimpleUploadedFile("avatar.gif", _tiny_gif_bytes(), content_type="image/gif")
        response = self.client.post(
            self.url,
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "profile@example.com",
                "phone": "",
                "bio": "",
                "city": "",
                "avatar": gif_file,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "نوع الملف غير مدعوم")
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.avatar)

    def test_oversized_image_rejected_as_avatar(self):
        self.client.force_login(self.user)
        # IMAGE_MAX_SIZE_MB is 5 — pad a valid PNG past that.
        big_file = SimpleUploadedFile(
            "avatar.png", _tiny_png_bytes(padding=6 * 1024 * 1024), content_type="image/png"
        )
        response = self.client.post(
            self.url,
            data={
                "first_name": "Updated",
                "last_name": "Name",
                "email": "profile@example.com",
                "phone": "",
                "bio": "",
                "city": "",
                "avatar": big_file,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حجم الملف كبير جدًا")
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.avatar)
