from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from . import services
from .forms import LoginForm, ProfileForm, SignupForm
from .models import EmailVerification


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


class SignupView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("accounts:signup-check-email")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_social_provider_flags())
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        user = services.create_local_user(
            email=data["email"],
            phone=data.get("full_phone"),
            full_name=data["full_name"],
            password=data["password1"],
        )
        services.send_activation_email(user, request=self.request)
        self.request.session["signup_email"] = user.email
        return super().form_valid(form)


class SignupCheckEmailView(TemplateView):
    template_name = "accounts/signup_check_email.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.session.get("signup_email", "")
        return context


class VerifyEmailView(View):
    def get(self, request, token):
        verification = get_object_or_404(EmailVerification, token=token)
        if verification.verified_at is None and verification.expires_at >= timezone.now():
            verification.verified_at = timezone.now()
            verification.save(update_fields=["verified_at"])
            user = verification.user
            user.is_active = True
            user.is_email_verified = True
            user.save(update_fields=["is_active", "is_email_verified"])
            login(request, user, backend="apps.accounts.backends.EmailOrPhoneBackend")
            messages.success(request, "تم تفعيل حسابك بنجاح.")
            return redirect("accounts:profile")

        messages.error(request, "رابط التفعيل غير صالح أو منتهي الصلاحية.")
        return redirect("accounts:login")


class LoginView(FormView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_social_provider_flags())
        return context

    def form_valid(self, form):
        user = authenticate(
            self.request,
            username=form.cleaned_data["identifier"],
            password=form.cleaned_data["password"],
        )
        if user is None:
            form.add_error(None, "بيانات الدخول غير صحيحة.")
            return self.form_invalid(form)
        if not user.is_active:
            form.add_error(None, "الحساب غير مفعّل بعد، برجاء تفعيله عبر البريد الإلكتروني.")
            return self.form_invalid(form)
        login(self.request, user)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.request.GET.get("next") or reverse_lazy("accounts:profile")


class ProfileEditView(LoginRequiredMixin, View):
    template_name = "accounts/profile_edit.html"
    login_url = reverse_lazy("accounts:login")

    def get(self, request):
        profile_form = ProfileForm(instance=request.user.profile, user=request.user)
        password_form = PasswordChangeForm(user=request.user)
        return render(
            request,
            self.template_name,
            {"profile_form": profile_form, "password_form": password_form},
        )

    def post(self, request):
        profile_form = ProfileForm(
            request.POST, request.FILES, instance=request.user.profile, user=request.user
        )
        password_form = PasswordChangeForm(user=request.user)

        if "change_password" in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, "تم تغيير كلمة المرور بنجاح.")
                return redirect("accounts:profile")
        elif profile_form.is_valid():
            profile_form.save()
            messages.success(request, "تم تحديث الملف الشخصي بنجاح.")
            return redirect("accounts:profile")

        return render(
            request,
            self.template_name,
            {"profile_form": profile_form, "password_form": password_form},
        )
