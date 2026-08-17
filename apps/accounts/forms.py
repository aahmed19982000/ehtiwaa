from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.countries import DEFAULT_DIAL_CODE, DIAL_CODE_CHOICES

from .models import Profile, User


class LoginForm(forms.Form):
    email = forms.EmailField(label=_("البريد الإلكتروني"))
    password = forms.CharField(
        label=_("كلمة المرور"), widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label=_("البريد الإلكتروني"))


class SignupForm(forms.Form):
    full_name = forms.CharField(label=_("الاسم"), max_length=150)
    email = forms.EmailField(label=_("البريد الإلكتروني"))
    country_code = forms.ChoiceField(
        label=_("مفتاح الدولة"), choices=DIAL_CODE_CHOICES, initial=DEFAULT_DIAL_CODE
    )
    phone = forms.CharField(label=_("رقم الهاتف"), max_length=20)
    password1 = forms.CharField(
        label=_("كلمة المرور"),
        min_length=8,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("8 أحرف على الأقل."),
    )
    password2 = forms.CharField(
        label=_("تأكيد كلمة المرور"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    agree_terms = forms.BooleanField(
        label=_("أوافق على الشروط والأحكام وسياسة الخصوصية"), required=True
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("هذا البريد الإلكتروني مستخدم بالفعل."))
        return email

    def clean_password1(self):
        password1 = self.cleaned_data["password1"]
        validate_password(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()

        country_code = cleaned_data.get("country_code")
        phone = cleaned_data.get("phone")
        if country_code and phone:
            full_phone = f"{country_code}{phone.lstrip('0')}"
            if User.objects.filter(phone=full_phone).exists():
                self.add_error("phone", _("رقم الهاتف مستخدم بالفعل."))
            cleaned_data["full_phone"] = full_phone

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", _("كلمتا المرور غير متطابقتين."))

        return cleaned_data


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label=_("الاسم الأول"), max_length=150, required=False)
    last_name = forms.CharField(label=_("اسم العائلة"), max_length=150, required=False)
    email = forms.EmailField(label=_("البريد الإلكتروني"))
    phone = forms.CharField(label=_("رقم الهاتف"), max_length=20, required=False)

    class Meta:
        model = Profile
        fields = ["avatar", "bio", "city"]
        labels = {
            "avatar": _("الصورة الشخصية"),
            "bio": _("نبذة تعريفية"),
            "city": _("المدينة"),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError(_("هذا البريد الإلكتروني مستخدم بالفعل."))
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user is not None:
            self.user.first_name = self.cleaned_data["first_name"]
            self.user.last_name = self.cleaned_data["last_name"]
            self.user.email = self.cleaned_data["email"]
            self.user.phone = self.cleaned_data["phone"] or None
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile
