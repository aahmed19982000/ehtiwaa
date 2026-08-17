from allauth.account.utils import user_email
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from .models import Profile, User


class EhtiwaaSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Auth0 (Google + Database/username-password connection) is the only
    signup/login path in this app. Links a social login to an existing local
    account sharing the same email instead of erroring out, but only when the
    provider has actually verified that email — otherwise anyone could type
    in someone else's email address on Auth0's Database connection and get
    silently connected to their account."""

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        email = user_email(sociallogin.user)
        if not email:
            return
        existing = User.objects.filter(email__iexact=email).first()
        if not existing:
            return

        if not sociallogin.account.extra_data.get("email_verified"):
            messages.error(
                request,
                _(
                    "هذا البريد الإلكتروني مسجّل بحساب موجود ولم يتم توثيقه بعد من مزود "
                    "الدخول. برجاء توثيق بريدك الإلكتروني أولًا ثم إعادة المحاولة."
                ),
            )
            raise ImmediateHttpResponse(redirect("accounts:welcome"))

        # A pre-existing account may predate this app requiring Auth0 (or may
        # simply be inactive) — bring it in sync, otherwise ModelBackend.get_user()
        # logs it straight back out on the very next request.
        if not existing.is_active or not existing.is_email_verified:
            existing.is_active = True
            existing.is_email_verified = True
            existing.save(update_fields=["is_active", "is_email_verified"])

        sociallogin.connect(request, existing)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.is_active = True
        user.is_email_verified = bool(sociallogin.account.extra_data.get("email_verified"))
        user.set_unusable_password()
        user.save(update_fields=["is_active", "is_email_verified", "password"])
        Profile.objects.get_or_create(user=user)
        return user
