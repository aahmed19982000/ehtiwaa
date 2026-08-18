from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.core.countries import COUNTRY_CHOICES, DEFAULT_DIAL_CODE, DIAL_CODE_CHOICES
from apps.core.validators import (
    validate_document_content,
    validate_document_extension,
    validate_document_size,
)

from .models import LANGUAGE_CHOICES, Specialist

# Shared by every credential-document field below — rejects disallowed
# extensions (e.g. .exe, .php), files over the size cap, and content that
# doesn't match the claimed extension. See apps/core/validators.py.
DOCUMENT_VALIDATORS = [
    validate_document_extension,
    validate_document_size,
    validate_document_content,
]

# Required credential documents per category — used both to render the
# right upload fields and (server-side) to enforce them in clean().
CATEGORY_DOCUMENTS = {
    "psychiatrist": [
        ("degree_certificate", _("شهادة التخرج")),
        ("license_file", _("رخصة مزاولة المهنة")),
        ("syndicate_card", _("شهادة نقابة الأطباء")),
        ("postgraduate_certificate", _("شهادة الدراسات العليا (ماجستير أو دكتوراه)")),
    ],
    "clinical_psychologist": [
        ("degree_certificate", _("شهادة الماجستير في علم النفس الاكلينيكي")),
        ("supervision_proof", _("إثبات وثيقة الإشراف")),
    ],
    "counselor": [
        ("degree_certificate", _("شهادة الماجستير في علم النفس")),
        ("supervision_proof", _("إثبات وثيقة الإشراف")),
    ],
}

MIN_EXPERIENCE_YEARS = 5


SORT_CHOICES = [
    ("rating", _("الأعلى تقييمًا")),
    ("price_asc", _("الأقل سعرًا")),
    ("availability", _("الأقرب توفرًا")),
]

DURATION_CHOICES = [
    ("", _("كل المدد")),
    ("60", _("60 دقيقة")),
    ("30", _("30 دقيقة")),
]

MIN_RATING_CHOICES = [
    ("", _("أي تقييم")),
    ("4", _("4 نجوم فأكثر")),
    ("3", _("3 نجوم فأكثر")),
    ("2", _("نجمتان فأكثر")),
    ("1", _("نجمة فأكثر")),
]


class SpecialistDirectoryFilterForm(forms.Form):
    """GET-based search/filter/sort controls for the public directory
    (SpecialistDirectoryView) — every field is optional so an empty
    querystring just shows the full approved list."""

    q = forms.CharField(label=_("بحث"), required=False)
    category = forms.ChoiceField(
        label=_("التخصص"),
        choices=[("", _("كل التخصصات"))] + Specialist.CATEGORY_CHOICES,
        required=False,
    )
    gender = forms.ChoiceField(
        label=_("الجنس"),
        choices=[("", _("الكل"))] + Specialist.GENDER_CHOICES,
        required=False,
    )
    language = forms.ChoiceField(
        label=_("اللغة"),
        choices=[("", _("كل اللغات"))] + LANGUAGE_CHOICES,
        required=False,
    )
    duration = forms.ChoiceField(label=_("مدة الجلسة"), choices=DURATION_CHOICES, required=False)
    min_rating = forms.ChoiceField(
        label=_("الحد الأدنى للتقييم"), choices=MIN_RATING_CHOICES, required=False
    )
    # Shortcut for category="psychiatrist" — only a psychiatrist (a
    # licensed physician) can legally prescribe medication; clinical
    # psychologists/counselors can't, regardless of experience.
    can_prescribe = forms.BooleanField(label=_("يقدر يصف دواء"), required=False)
    price_min = forms.IntegerField(label=_("السعر من"), required=False, min_value=0)
    price_max = forms.IntegerField(label=_("السعر إلى"), required=False, min_value=0)
    available_only = forms.BooleanField(label=_("متاح للحجز قريبًا فقط"), required=False)
    sort = forms.ChoiceField(
        label=_("الترتيب"), choices=SORT_CHOICES, required=False, initial="rating"
    )

    def clean(self):
        cleaned_data = super().clean()
        price_min = cleaned_data.get("price_min")
        price_max = cleaned_data.get("price_max")
        if price_min is not None and price_max is not None and price_min > price_max:
            self.add_error("price_max", _("السعر الأقصى لازم يكون أكبر من أو يساوي الأدنى."))
        return cleaned_data

    def has_active_filters(self):
        if not self.is_bound:
            return False
        data = self.cleaned_data if hasattr(self, "cleaned_data") else {}
        return any(
            data.get(field)
            for field in (
                "q",
                "category",
                "gender",
                "language",
                "duration",
                "min_rating",
                "can_prescribe",
                "price_min",
                "price_max",
                "available_only",
            )
        )


class SpecialistApplicationForm(forms.Form):
    category = forms.ChoiceField(
        label=_("الفئة"),
        choices=Specialist.CATEGORY_CHOICES,
        widget=forms.RadioSelect(attrs={"data-category-radio": "true"}),
    )

    full_name_ar = forms.CharField(label=_("الاسم بالكامل (بالعربية)"), max_length=255)
    full_name_en = forms.CharField(label=_("الاسم بالكامل (بالإنجليزية)"), max_length=255)
    title = forms.ChoiceField(label=_("اللقب"), choices=Specialist.TITLE_CHOICES)
    country_code = forms.ChoiceField(
        label=_("مفتاح الدولة"), choices=DIAL_CODE_CHOICES, initial=DEFAULT_DIAL_CODE
    )
    phone = forms.CharField(label=_("رقم التليفون"), max_length=20)
    birth_year = forms.IntegerField(label=_("سنة الميلاد"), min_value=1930, max_value=2015)
    gender = forms.ChoiceField(label=_("الجنس"), choices=Specialist.GENDER_CHOICES)
    nationality = forms.ChoiceField(label=_("الجنسية"), choices=COUNTRY_CHOICES)
    country_of_residence = forms.ChoiceField(label=_("بلد الإقامة"), choices=COUNTRY_CHOICES)
    languages = forms.MultipleChoiceField(
        label=_("اللغات المتحدث بها بطلاقة"),
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    years_of_experience = forms.IntegerField(label=_("سنوات الخبرة"), required=False, min_value=0)

    agree_terms = forms.BooleanField(
        label=_("أوافق على الشروط والأحكام وسياسة الخصوصية"), required=True
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        # Anonymous visitors don't have an account yet — collect one here
        # (matching Shezlong's own registration form, which folds account
        # creation into the same page) instead of gating behind a separate
        # signup step first.
        self.needs_account = user is None or not user.is_authenticated
        super().__init__(*args, **kwargs)
        if self.needs_account:
            self.fields["email"] = forms.EmailField(label=_("البريد الإلكتروني"))
            self.fields["password1"] = forms.CharField(
                label=_("كلمة المرور"),
                min_length=8,
                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
                help_text=_("8 أحرف على الأقل."),
            )
            self.fields["password2"] = forms.CharField(
                label=_("تأكيد كلمة المرور"),
                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
            )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("هذا البريد الإلكتروني مستخدم بالفعل."))
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
            phone_qs = User.objects.filter(phone=full_phone)
            if self.user and self.user.is_authenticated:
                phone_qs = phone_qs.exclude(pk=self.user.pk)
            if phone_qs.exists():
                self.add_error("phone", _("رقم الهاتف مستخدم بالفعل."))
            cleaned_data["full_phone"] = full_phone

        if self.needs_account:
            password1 = cleaned_data.get("password1")
            password2 = cleaned_data.get("password2")
            if password1 and password2 and password1 != password2:
                self.add_error("password2", _("كلمتا المرور غير متطابقتين."))

        category = cleaned_data.get("category")
        if category in ("clinical_psychologist", "counselor"):
            years = cleaned_data.get("years_of_experience")
            if years is None or years < MIN_EXPERIENCE_YEARS:
                self.add_error(
                    "years_of_experience",
                    _("مطلوب %(years)s سنوات خبرة على الأقل لهذه الفئة.")
                    % {"years": MIN_EXPERIENCE_YEARS},
                )
        return cleaned_data


class SpecialistDocumentsForm(forms.Form):
    """Step 2 — shown only after the account/application (step 1) already
    exists, so the specialist's category is already known and this only
    renders/requires the document fields relevant to it."""

    degree_certificate = forms.FileField(required=False, validators=DOCUMENT_VALIDATORS)
    license_file = forms.FileField(required=False, validators=DOCUMENT_VALIDATORS)
    syndicate_card = forms.FileField(required=False, validators=DOCUMENT_VALIDATORS)
    postgraduate_certificate = forms.FileField(required=False, validators=DOCUMENT_VALIDATORS)
    supervision_proof = forms.FileField(required=False, validators=DOCUMENT_VALIDATORS)

    def __init__(self, *args, category=None, **kwargs):
        self.category = category
        self.required_documents = CATEGORY_DOCUMENTS.get(category, [])
        super().__init__(*args, **kwargs)
        relevant_fields = {field_name for field_name, _label in self.required_documents}
        for field_name in list(self.fields):
            if field_name not in relevant_fields:
                del self.fields[field_name]
            else:
                self.fields[field_name].label = dict(self.required_documents)[field_name]

    def clean(self):
        cleaned_data = super().clean()
        for field_name, doc_label in self.required_documents:
            if not cleaned_data.get(field_name):
                self.add_error(field_name, _("هذا المستند مطلوب: %(doc)s") % {"doc": doc_label})
        return cleaned_data

    def documents(self):
        """[(field_name, label, uploaded_file), ...] — used by the view to
        create CredentialDocument rows."""
        result = []
        for field_name, doc_label in self.required_documents:
            uploaded = self.cleaned_data.get(field_name)
            if uploaded:
                result.append((field_name, doc_label, uploaded))
        return result
