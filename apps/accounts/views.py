from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from . import auth0
from .forms import ForgotPasswordForm, LoginForm, ProfileForm, SignupForm


def _social_provider_flags():
    return {
        "google_enabled": bool(settings.SOCIALACCOUNT_PROVIDERS.get("google", {}).get("APPS")),
        "auth0_enabled": bool(settings.SOCIALACCOUNT_PROVIDERS.get("auth0", {}).get("APPS")),
    }


class WelcomeView(TemplateView):
    template_name = "accounts/welcome.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_social_provider_flags())
        return context


class Auth0RedirectView(View):
    """Sends the browser straight into Auth0's hosted Universal Login page.
    No longer linked from accounts:login (LoginView has its own branded
    form now) — kept for allauth's account_login fallback (see
    config/urls.py) and as a manual escape hatch to the hosted page."""

    screen_hint = None

    def get(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("تسجيل الدخول غير متاح حاليًا."))
            return redirect("accounts:welcome")

        provider = get_adapter().get_provider(request, "auth0")
        kwargs = {"process": "login"}
        next_url = request.GET.get(REDIRECT_FIELD_NAME)
        if next_url:
            kwargs[REDIRECT_FIELD_NAME] = next_url
        # prompt=login forces Auth0 to show the login/signup screen even when
        # the browser still has an Auth0 SSO session from an earlier test —
        # without it, clicking "signup" while already logged in silently
        # reuses that session and jumps straight to the "Authorize App"
        # consent screen instead of the actual signup form.
        auth_params = ["prompt=login"]
        if self.screen_hint:
            auth_params.append(f"screen_hint={self.screen_hint}")
        kwargs["auth_params"] = "&".join(auth_params)
        return redirect(provider.get_login_url(request, **kwargs))


class SignupView(View):
    """Our own branded, two-step signup form — collects name/email/phone
    then password, unlike Auth0RedirectView which bounces straight to
    Auth0's hosted page. Talks to Auth0's Authentication API directly
    (apps.accounts.auth0) so the account still lives in Auth0's Database
    connection, then hands off to allauth's normal social-login pipeline
    (EhtiwaaSocialAccountAdapter) so the resulting local User/SocialAccount
    are indistinguishable from one created via the hosted login page."""

    template_name = "accounts/signup.html"

    def get(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("التسجيل غير متاح حاليًا."))
            return redirect("accounts:welcome")
        return render(request, self.template_name, {"form": SignupForm()})

    def post(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("التسجيل غير متاح حاليًا."))
            return redirect("accounts:welcome")

        form = SignupForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        email = form.cleaned_data["email"]
        password = form.cleaned_data["password1"]
        full_name = form.cleaned_data["full_name"].strip()
        full_phone = form.cleaned_data["full_phone"]

        signup_failed_login_error = _("تم إنشاء حسابك، لكن تعذّر تسجيل دخولك تلقائيًا.")
        try:
            auth0.signup(email=email, password=password, name=full_name)
            token_data = auth0.login(
                email=email, password=password, generic_error=signup_failed_login_error
            )
            userinfo = auth0.get_userinfo(
                token_data["access_token"], generic_error=signup_failed_login_error
            )
        except auth0.Auth0Error as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, {"form": form})

        provider = get_adapter().get_provider(request, "auth0")
        sociallogin = provider.sociallogin_from_response(request, userinfo)

        name_parts = full_name.split(" ", 1)
        sociallogin.user.first_name = name_parts[0]
        sociallogin.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        sociallogin.user.phone = full_phone

        return complete_social_login(request, sociallogin)


class LoginView(View):
    """Our own branded, two-step login form (email → password), same
    approach as SignupView: talks to Auth0's Authentication API directly
    (Resource Owner Password Grant) instead of bouncing to Auth0's hosted
    Universal Login page, then hands off to the same social-login pipeline
    so returning users are recognized by their existing SocialAccount."""

    template_name = "accounts/login.html"

    def get(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("تسجيل الدخول غير متاح حاليًا."))
            return redirect("accounts:welcome")
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("تسجيل الدخول غير متاح حاليًا."))
            return redirect("accounts:welcome")

        form = LoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        try:
            token_data = auth0.login(
                email=form.cleaned_data["email"], password=form.cleaned_data["password"]
            )
            userinfo = auth0.get_userinfo(token_data["access_token"])
        except auth0.Auth0Error as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, {"form": form})

        provider = get_adapter().get_provider(request, "auth0")
        sociallogin = provider.sociallogin_from_response(request, userinfo)
        return complete_social_login(request, sociallogin)


class ForgotPasswordView(View):
    """Triggers Auth0's own password-reset email — separate from
    accounts:password-reset, which is the local Django flow kept only for
    staff/admin accounts with a real (non-Auth0) usable password."""

    template_name = "accounts/forgot_password.html"

    def get(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("هذه الخدمة غير متاحة حاليًا."))
            return redirect("accounts:welcome")
        return render(request, self.template_name, {"form": ForgotPasswordForm()})

    def post(self, request):
        if not _social_provider_flags()["auth0_enabled"]:
            messages.error(request, _("هذه الخدمة غير متاحة حاليًا."))
            return redirect("accounts:welcome")

        form = ForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        try:
            auth0.request_password_change(form.cleaned_data["email"])
        except auth0.Auth0Error as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, {"form": form})

        return render(request, self.template_name, {"form": form, "sent": True})


class ProfileEditView(LoginRequiredMixin, View):
    template_name = "accounts/profile_edit.html"
    login_url = reverse_lazy("accounts:login")

    def get(self, request):
        profile_form = ProfileForm(instance=request.user.profile, user=request.user)
        return render(request, self.template_name, {"profile_form": profile_form})

    def post(self, request):
        profile_form = ProfileForm(
            request.POST, request.FILES, instance=request.user.profile, user=request.user
        )
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, _("تم تحديث الملف الشخصي بنجاح."))
            return redirect("accounts:profile")

        return render(request, self.template_name, {"profile_form": profile_form})
