from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.core.countries import DEFAULT_DIAL_CODE, DIAL_CODE_CHOICES

from .models import Profile, User


class SignupForm(forms.Form):
    full_name = forms.CharField(label="الأسم", max_length=150)
    email = forms.EmailField(label="البريد الإلكتروني")
    country_code = forms.ChoiceField(
        label="مفتاح الدولة", choices=DIAL_CODE_CHOICES, initial=DEFAULT_DIAL_CODE
    )
    phone = forms.CharField(label="رقم الهاتف", max_length=20)
    password1 = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)
    password2 = forms.CharField(label="تأكيد كلمة المرور", widget=forms.PasswordInput)
    agree_terms = forms.BooleanField(
        label="أوافق على الشروط والأحكام وسياسة الخصوصية", required=True
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "كلمتا المرور غير متطابقتين.")
        elif password1:
            validate_password(password1)

        country_code = cleaned_data.get("country_code")
        phone = cleaned_data.get("phone")
        if country_code and phone:
            full_phone = f"{country_code}{phone.lstrip('0')}"
            if User.objects.filter(phone=full_phone).exists():
                self.add_error("phone", "رقم الهاتف مستخدم بالفعل.")
            cleaned_data["full_phone"] = full_phone
        return cleaned_data


class LoginForm(forms.Form):
    identifier = forms.CharField(label="البريد الإلكتروني أو رقم الهاتف")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label="الاسم الأول", max_length=150, required=False)
    last_name = forms.CharField(label="اسم العائلة", max_length=150, required=False)
    email = forms.EmailField(label="البريد الإلكتروني")
    phone = forms.CharField(label="رقم الهاتف", max_length=20, required=False)

    class Meta:
        model = Profile
        fields = ["avatar", "bio", "city"]
        labels = {"avatar": "الصورة الشخصية", "bio": "نبذة تعريفية", "city": "المدينة"}

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
            raise forms.ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
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
