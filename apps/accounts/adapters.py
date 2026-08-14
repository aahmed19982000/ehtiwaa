from allauth.account.utils import user_email
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Profile, User


class EhtiwaaSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Google/Auth0 login only (local email+password signup/login is
    hand-rolled elsewhere in this app). Links a social login to an existing
    local account sharing the same email instead of erroring out, and marks
    freshly-created accounts as active/verified since the provider already
    verified the email address."""

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        email = user_email(sociallogin.user)
        if not email:
            return
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            sociallogin.connect(request, existing)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.is_active = True
        user.is_email_verified = True
        user.set_unusable_password()
        user.save(update_fields=["is_active", "is_email_verified", "password"])
        Profile.objects.get_or_create(user=user)
        return user
