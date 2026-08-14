import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import EmailVerification, Profile, User

VERIFICATION_TOKEN_TTL = timedelta(hours=48)


def _unique_username(base):
    base = base or "user"
    username = base
    suffix = 0
    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base}{suffix}"
    return username


def create_local_user(*, email, phone, full_name, password, role="client", username=None):
    """Create a User + Profile pair from the signup / specialist-application
    forms. The account stays inactive until the caller sends an activation
    link via send_activation_email() and the user follows it."""
    first_name, _, last_name = full_name.strip().partition(" ")
    username = _unique_username(username or email.split("@", 1)[0])

    user = User(
        username=username,
        email=email,
        phone=phone or None,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=False,
    )
    user.set_password(password)
    user.save()
    Profile.objects.create(user=user)
    return user


def send_activation_email(user, request=None):
    token = secrets.token_urlsafe(32)
    EmailVerification.objects.create(
        user=user,
        token=token,
        expires_at=timezone.now() + VERIFICATION_TOKEN_TTL,
    )

    path = reverse("accounts:verify-email", kwargs={"token": token})
    activation_url = request.build_absolute_uri(path) if request else path

    message = render_to_string(
        "accounts/email/activation_email.txt",
        {"user": user, "activation_url": activation_url},
    )
    send_mail(
        subject="تفعيل حسابك في احتواء",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
