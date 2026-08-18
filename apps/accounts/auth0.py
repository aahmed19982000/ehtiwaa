"""Thin client around Auth0's Authentication API, used only by SignupView
(apps.accounts.views) to power our own signup form. Everything else
(login, password reset) still goes through Auth0's hosted Universal Login
via Auth0RedirectView + django-allauth's OAuth2 flow.
"""

import requests
from django.conf import settings


class Auth0Error(Exception):
    """Raised with a message already safe to show the user."""


def _base_url():
    return f"https://{settings.AUTH0_DOMAIN}"


def signup(*, email, password, name):
    """Creates a user on Auth0's Database connection. Raises Auth0Error with
    an Arabic, user-facing message on failure."""
    try:
        resp = requests.post(
            f"{_base_url()}/dbconnections/signup",
            json={
                "client_id": settings.AUTH0_CLIENT_ID,
                "email": email,
                "password": password,
                "connection": settings.AUTH0_DB_CONNECTION,
                "name": name,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise Auth0Error("تعذّر الاتصال بخدمة التسجيل. برجاء المحاولة مرة أخرى.") from exc

    if resp.ok:
        return resp.json()

    data = (
        resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    )
    code = data.get("code") or data.get("name")
    if code == "user_exists":
        raise Auth0Error("هذا البريد الإلكتروني مسجّل بحساب موجود بالفعل.")
    if code in (
        "invalid_password",
        "PasswordStrengthError",
        "PasswordDictionaryError",
        "PasswordNoUserInfoError",
    ):
        raise Auth0Error(_password_policy_message(data))
    raise Auth0Error(data.get("description") or "تعذّر إنشاء الحساب. برجاء المحاولة مرة أخرى.")


def _password_policy_message(data):
    """Auth0's dbconnections/signup password rejection includes exactly
    which rule failed (data["description"]["rules"]) — surface the concrete
    reason (e.g. minimum length) instead of a generic "weak password" that
    doesn't tell the user what to fix. Our own SignupForm/
    SpecialistApplicationForm already enforce the same rules client- and
    server-side (see AUTH_PASSWORD_VALIDATORS), so this is mainly a
    safety net for whenever the two drift out of sync."""
    description = data.get("description")
    rules = description.get("rules", []) if isinstance(description, dict) else []
    for rule in rules:
        if rule.get("verified"):
            continue
        if rule.get("code") == "lengthAtLeast" and rule.get("format"):
            return f"كلمة المرور يجب أن تكون {rule['format'][0]} حرفًا على الأقل."
    return "كلمة المرور ضعيفة، برجاء اختيار كلمة مرور أقوى."


def login(*, email, password, generic_error=None):
    """Resource Owner Password Grant against our Database connection.
    Requires the "Password" grant type enabled on the Auth0 application.
    `generic_error` lets callers (e.g. SignupView, right after its own
    signup() call) override the fallback message for non-credential
    failures — the default here is written for the plain login form."""
    generic_error = generic_error or "تعذّر تسجيل الدخول. برجاء المحاولة مرة أخرى."
    try:
        resp = requests.post(
            f"{_base_url()}/oauth/token",
            json={
                "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
                "realm": settings.AUTH0_DB_CONNECTION,
                "username": email,
                "password": password,
                "client_id": settings.AUTH0_CLIENT_ID,
                "client_secret": settings.AUTH0_CLIENT_SECRET,
                "scope": "openid profile email",
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise Auth0Error(generic_error) from exc

    if resp.ok:
        return resp.json()

    data = (
        resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    )
    if data.get("error") == "invalid_grant":
        raise Auth0Error("البريد الإلكتروني أو كلمة المرور غير صحيحة.")
    raise Auth0Error(generic_error)


def get_userinfo(access_token, generic_error=None):
    generic_error = generic_error or "تعذّر تسجيل الدخول. برجاء المحاولة مرة أخرى."
    try:
        resp = requests.get(
            f"{_base_url()}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise Auth0Error(generic_error) from exc

    if not resp.ok:
        raise Auth0Error(generic_error)
    return resp.json()


def request_password_change(email):
    """Triggers Auth0's own password-reset email for the Database
    connection. Always looks like it succeeded regardless of whether the
    email exists — that's Auth0's own anti-enumeration behavior, and we
    keep it since it doesn't reveal registered emails to attackers."""
    try:
        resp = requests.post(
            f"{_base_url()}/dbconnections/change_password",
            json={
                "client_id": settings.AUTH0_CLIENT_ID,
                "email": email,
                "connection": settings.AUTH0_DB_CONNECTION,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise Auth0Error("تعذّر إرسال رابط إعادة التعيين. برجاء المحاولة مرة أخرى.") from exc

    if not resp.ok:
        raise Auth0Error("تعذّر إرسال رابط إعادة التعيين. برجاء المحاولة مرة أخرى.")
