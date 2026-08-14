from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.core.countries import COUNTRY_CHOICES, DEFAULT_DIAL_CODE, DIAL_CODE_CHOICES

from .models import Specialist

LANGUAGE_CHOICES = [
    ("ar", "العربية"),
    ("en", "الإنجليزية"),
    ("fr", "الفرنسية"),
    ("de", "الألمانية"),
    ("es", "الإسبانية"),
    ("it", "الإيطالية"),
    ("tr", "التركية"),
    ("ur", "الأردية"),
    ("zh", "الصينية"),
]

# Required credential documents per category — used both to render the
# right upload fields and (server-side) to enforce them in clean().
CATEGORY_DOCUMENTS = {
    "psychiatrist": [
        ("degree_certificate", "شهادة التخرج"),
        ("license_file", "رخصة مزاولة المهنة"),
        ("syndicate_card", "شهادة نقابة الأطباء"),
        ("postgraduate_certificate", "شهادة الدراسات العليا (ماجستير أو دكتوراه)"),
    ],
    "clinical_psychologist": [
        ("degree_certificate", "شهادة الماجستير في علم النفس الاكلينيكي"),
        ("supervision_proof", "إثبات وثيقة الإشراف"),
    ],
    "counselor": [
        ("degree_certificate", "شهادة الماجستير في علم النفس"),
        ("supervision_proof", "إثبات وثيقة الإشراف"),
    ],
}

MIN_EXPERIENCE_YEARS = 5


class SpecialistApplicationForm(forms.Form):
    category = forms.ChoiceField(
        label="الفئة",
        choices=Specialist.CATEGORY_CHOICES,
        widget=forms.RadioSelect(attrs={"data-category-radio": "true"}),
    )

    full_name_ar = forms.CharField(label="الاسم بالكامل (بالعربية)", max_length=255)
    full_name_en = forms.CharField(label="الاسم بالكامل (بالإنجليزية)", max_length=255)
    title = forms.ChoiceField(label="اللقب", choices=Specialist.TITLE_CHOICES)
    email = forms.EmailField(label="البريد الإلكتروني")
    country_code = forms.ChoiceField(
        label="مفتاح الدولة", choices=DIAL_CODE_CHOICES, initial=DEFAULT_DIAL_CODE
    )
    phone = forms.CharField(label="رقم التليفون", max_length=20)
    username = forms.CharField(label="اسم المستخدم", max_length=150)
    birth_year = forms.IntegerField(label="سنة الميلاد", min_value=1930, max_value=2015)
    gender = forms.ChoiceField(label="الجنس", choices=Specialist.GENDER_CHOICES)
    nationality = forms.ChoiceField(label="الجنسية", choices=COUNTRY_CHOICES)
    country_of_residence = forms.ChoiceField(label="بلد الإقامة", choices=COUNTRY_CHOICES)
    languages = forms.MultipleChoiceField(
        label="اللغات المتحدث بها بطلاقة",
        choices=LANGUAGE_CHOICES,
        widget=forms.SelectMultiple,
    )

    years_of_experience = forms.IntegerField(label="سنوات الخبرة", required=False, min_value=0)

    degree_certificate = forms.FileField(label="شهادة الماجستير / شهادة التخرج", required=False)
    license_file = forms.FileField(label="رخصة مزاولة المهنة", required=False)
    syndicate_card = forms.FileField(label="شهادة نقابة الأطباء", required=False)
    postgraduate_certificate = forms.FileField(label="شهادة الدراسات العليا", required=False)
    supervision_proof = forms.FileField(label="إثبات وثيقة الإشراف", required=False)

    password1 = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)
    password2 = forms.CharField(label="تأكيد كلمة المرور", widget=forms.PasswordInput)
    agree_terms = forms.BooleanField(
        label="أوافق على الشروط والأحكام وسياسة الخصوصية", required=True
    )

    def clean_email(self):
        from apps.accounts.models import User

        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")
        return email

    def clean_username(self):
        from apps.accounts.models import User

        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("اسم المستخدم مستخدم بالفعل.")
        return username

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
            cleaned_data["full_phone"] = f"{country_code}{phone.lstrip('0')}"

        category = cleaned_data.get("category")
        if category:
            if category in ("clinical_psychologist", "counselor"):
                years = cleaned_data.get("years_of_experience")
                if years is None or years < MIN_EXPERIENCE_YEARS:
                    self.add_error(
                        "years_of_experience",
                        f"مطلوب {MIN_EXPERIENCE_YEARS} سنوات خبرة على الأقل لهذه الفئة.",
                    )
            for field_name, doc_label in CATEGORY_DOCUMENTS.get(category, []):
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, f"هذا المستند مطلوب: {doc_label}")

        return cleaned_data

    def documents_for_category(self):
        """[(field_name, label, uploaded_file), ...] for the selected
        category — used by the view to create CredentialDocument rows."""
        category = self.cleaned_data.get("category")
        result = []
        for field_name, doc_label in CATEGORY_DOCUMENTS.get(category, []):
            uploaded = self.cleaned_data.get(field_name)
            if uploaded:
                result.append((field_name, doc_label, uploaded))
        return result
