from django import forms
from django.contrib.auth.models import Group, Permission
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.content.models import Article, Banner, Category, Testimonial, Video
from apps.core.models import HomepageContent
from apps.courses.models import Course
from apps.specialists.models import LANGUAGE_CHOICES, Specialist

from .models import Report
from .permissions import PANEL_CAPABILITIES, admin_eligible_users


class SpecialistChoiceField(forms.ModelChoiceField):
    """Specialist.__str__ is a debug repr ("Specialist<22>"), not a name —
    override the dropdown label so staff can actually tell rows apart."""

    def label_from_instance(self, obj):
        return obj.full_name_ar or obj.full_name_en or obj.user.email


class ReviewDecisionForm(forms.Form):
    notes = forms.CharField(
        label=_("ملاحظات (اختياري)"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )


class ReportGenerateForm(forms.Form):
    report_type = forms.ChoiceField(label=_("نوع التقرير"), choices=Report.REPORT_TYPE_CHOICES)
    date_from = forms.DateField(label=_("من تاريخ"), widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(label=_("إلى تاريخ"), widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(_("تاريخ البداية لازم يكون قبل تاريخ النهاية."))
        return cleaned_data


class PanelLoginForm(forms.Form):
    email = forms.EmailField(label=_("البريد الإلكتروني"))
    password = forms.CharField(
        label=_("كلمة المرور"),
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class SpecialistForm(forms.ModelForm):
    languages = forms.MultipleChoiceField(
        label=_("اللغات"),
        required=False,
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Specialist
        fields = [
            "status",
            "is_featured",
            "can_write_articles",
            "category",
            "title",
            "full_name_ar",
            "full_name_en",
            "headline",
            "about",
            "specialties",
            "years_of_experience",
            "license_number",
            "hourly_rate",
            "price_30min",
            "languages",
            "gender",
            "birth_year",
            "nationality",
            "country_of_residence",
        ]
        widgets = {"about": forms.Textarea(attrs={"rows": 4})}
        labels = {
            "status": _("الحالة"),
            "is_featured": _("مميز في الرئيسية"),
            "can_write_articles": _("مسموح له بكتابة مقالات"),
            "category": _("التخصص"),
            "title": _("اللقب"),
            "full_name_ar": _("الاسم بالعربية"),
            "full_name_en": _("الاسم بالإنجليزية"),
            "headline": _("العنوان التعريفي"),
            "about": _("نبذة تعريفية"),
            "specialties": _("الوسوم/التخصصات الدقيقة"),
            "years_of_experience": _("سنوات الخبرة"),
            "license_number": _("رقم الترخيص"),
            "hourly_rate": _("سعر الجلسة (60 دقيقة)"),
            "price_30min": _("سعر الجلسة (30 دقيقة)"),
            "gender": _("الجنس"),
            "birth_year": _("سنة الميلاد"),
            "nationality": _("الجنسية"),
            "country_of_residence": _("بلد الإقامة"),
        }


class SpecialistCreateForm(SpecialistForm):
    email = forms.EmailField(label=_("البريد الإلكتروني"))

    field_order = ["email"]


class CourseForm(forms.ModelForm):
    slug = forms.SlugField(label=_("الرابط المختصر (Slug)"), required=False)
    instructor = SpecialistChoiceField(
        queryset=Specialist.objects.all(), required=False, label=_("المحاضر")
    )

    class Meta:
        model = Course
        fields = [
            "title",
            "slug",
            "category",
            "description",
            "instructor",
            "price",
            "original_price",
            "is_published",
            "is_featured",
            "cover_image",
            "intro_video_url",
            "learning_outcomes",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}
        labels = {
            "title": _("العنوان"),
            "category": _("التصنيف"),
            "description": _("الوصف"),
            "instructor": _("المحاضر"),
            "price": _("السعر"),
            "original_price": _("السعر قبل الخصم"),
            "is_published": _("منشورة"),
            "is_featured": _("مميزة في الرئيسية"),
            "cover_image": _("صورة الغلاف"),
            "intro_video_url": _("رابط فيديو تعريفي"),
            "learning_outcomes": _("أهداف التعلم (سطر لكل هدف)"),
        }


class ArticleForm(forms.ModelForm):
    slug = forms.SlugField(label=_("الرابط المختصر (Slug)"), required=False)
    author = SpecialistChoiceField(
        queryset=Specialist.objects.filter(can_write_articles=True),
        required=False,
        label=_("الكاتب"),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label=_("التصنيف"),
        empty_label=_("بدون تصنيف"),
    )

    class Meta:
        model = Article
        fields = [
            "title",
            "slug",
            "category",
            "author",
            "body",
            "cover_image",
            "is_published",
            "meta_title",
            "meta_description",
            "title_en",
            "body_en",
            "meta_title_en",
            "meta_description_en",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "article-editor__title-input", "placeholder": _("عنوان المقال…")}
            ),
            "title_en": forms.TextInput(
                attrs={"class": "article-editor__title-input", "placeholder": "Article title…"}
            ),
            "body": forms.Textarea(attrs={"rows": 8, "class": "rich-text-source"}),
            "body_en": forms.Textarea(attrs={"rows": 8, "class": "rich-text-source"}),
        }
        labels = {
            "title": _("العنوان"),
            "category": _("التصنيف"),
            "author": _("الكاتب"),
            "body": _("المحتوى"),
            "cover_image": _("صورة الغلاف"),
            "meta_title": _("عنوان SEO"),
            "meta_description": _("وصف SEO"),
            "is_published": _("منشور"),
            "title_en": _("العنوان (إنجليزي)"),
            "body_en": _("المحتوى (إنجليزي)"),
            "meta_title_en": _("عنوان SEO (إنجليزي)"),
            "meta_description_en": _("وصف SEO (إنجليزي)"),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        labels = {"name": _("الاسم")}


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = [
            "title",
            "category",
            "description",
            "video_url",
            "thumbnail",
            "duration_seconds",
            "is_published",
            "is_featured",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        labels = {
            "title": _("العنوان"),
            "category": _("التصنيف"),
            "description": _("الوصف"),
            "video_url": _("رابط الفيديو"),
            "thumbnail": _("الصورة المصغرة"),
            "duration_seconds": _("المدة (ثانية)"),
            "is_published": _("منشور"),
            "is_featured": _("مميز في الرئيسية"),
        }


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ["title", "image", "link_url", "placement", "is_active", "starts_at", "ends_at"]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        labels = {
            "title": _("العنوان"),
            "image": _("الصورة"),
            "link_url": _("الرابط"),
            "placement": _("الموضع"),
            "is_active": _("مفعّل"),
            "starts_at": _("تاريخ البداية"),
            "ends_at": _("تاريخ النهاية"),
        }


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["author_name", "author_title", "photo", "quote", "is_active"]
        widgets = {"quote": forms.Textarea(attrs={"rows": 3})}
        labels = {
            "author_name": _("الاسم"),
            "author_title": _("الصفة/المسمى"),
            "photo": _("الصورة"),
            "quote": _("نص الرأي"),
            "is_active": _("مفعّل"),
        }


class HomepageContentForm(forms.ModelForm):
    class Meta:
        model = HomepageContent
        fields = ["hero_title", "hero_subtitle", "hero_image"]
        widgets = {"hero_subtitle": forms.Textarea(attrs={"rows": 3})}
        labels = {
            "hero_title": _("العنوان الرئيسي"),
            "hero_subtitle": _("الوصف الفرعي"),
            "hero_image": _("صورة الهيرو"),
        }


class RoleForm(forms.ModelForm):
    """A "role" is a plain Django Group — this form just wraps it with a
    friendlier surface: capability checkboxes (built from
    apps.adminpanel.permissions.PANEL_CAPABILITIES, so the same list drives
    both this UI and every view's `required_perms`) instead of raw
    permission codenames, plus which staff accounts hold the role."""

    # admin_eligible_users() excludes ordinary clients (accounts.User.role
    # == "client") but isn't restricted to is_staff=True — assigning a role
    # is often how a brand-new account becomes staff in the first place
    # (see _save_users below), so requiring is_staff first would make it
    # impossible to ever add someone new.
    users = forms.ModelMultipleChoiceField(
        queryset=admin_eligible_users(),
        required=False,
        label=_("المستخدمون"),
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ["name"]
        labels = {"name": _("اسم الدور")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for capability in PANEL_CAPABILITIES:
            self.fields[f"cap_{capability['key']}"] = forms.BooleanField(
                required=False, label=capability["label"]
            )
        if self.instance.pk:
            granted = {
                f"{app_label}.{codename}"
                for app_label, codename in self.instance.permissions.values_list(
                    "content_type__app_label", "codename"
                )
            }
            for capability in PANEL_CAPABILITIES:
                if granted & set(capability["perms"]):
                    self.fields[f"cap_{capability['key']}"].initial = True
            self.fields["users"].initial = self.instance.user_set.all()

    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit:
            self._save_permissions(group)
            self._save_users(group)
        return group

    def _save_permissions(self, group):
        codenames = []
        for capability in PANEL_CAPABILITIES:
            if self.cleaned_data.get(f"cap_{capability['key']}"):
                codenames.extend(capability["perms"])
        permissions = []
        for perm_path in codenames:
            app_label, codename = perm_path.split(".")
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permission:
                permissions.append(permission)
        group.permissions.set(permissions)

    def _save_users(self, group):
        new_members = self.cleaned_data.get("users") or User.objects.none()
        group.user_set.set(new_members)
        # Anyone assigned a panel role needs is_staff to actually log in —
        # only ever grants it here, never auto-revokes on removal (a user
        # might have other reasons to keep is_staff).
        new_members.filter(is_staff=False).update(is_staff=True)


class AdminForm(forms.ModelForm):
    """Full create/edit form for an admin account, used by both the
    Admins page's "+ إضافة أدمن" and its "تعديل" — same form either way,
    `self.instance.pk` tells save() which mode it's in. Not just email +
    role: name, phone, active status, panel role, and an optional password
    are all editable here, matching apps.adminpanel.forms.SpecialistForm's
    "edit everything about the account in one page" shape."""

    group = forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        label=_("الدور"),
        empty_label=_("بدون دور"),
    )
    password = forms.CharField(
        required=False,
        label=_("كلمة مرور جديدة"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_(
            "اتركها فارغة للإبقاء على كلمة المرور الحالية عند التعديل. عند "
            'الإضافة، تركها فارغة يولّد كلمة مرور عشوائية يقدر المستخدم '
            'تعيين كلمة مرور خاصة به بدلاً منها عبر "نسيت كلمة المرور".'
        ),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "is_active"]
        labels = {
            "email": _("البريد الإلكتروني"),
            "first_name": _("الاسم الأول"),
            "last_name": _("اسم العائلة"),
            "phone": _("رقم الهاتف"),
            "is_active": _("الحساب مفعّل"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["group"].initial = self.instance.groups.first()
            self.fields["password"].help_text = _("اتركها فارغة للإبقاء على كلمة المرور الحالية.")

            # can_write_articles lives on specialists.Specialist, not on
            # User — surfaced here too (not just from the Specialist edit
            # form) so an admin doesn't have to hop pages to grant it.
            # Disabled (not just hidden) when there's no linked specialist
            # profile, so it's clear *why* rather than silently missing.
            specialist_profile = getattr(self.instance, "specialist_profile", None)
            self.fields["can_write_articles"] = forms.BooleanField(
                required=False,
                label=_("مسموح له بكتابة مقالات"),
                disabled=specialist_profile is None,
                initial=specialist_profile.can_write_articles if specialist_profile else False,
                help_text=(
                    _('يتحكم في ظهوره كخيار "الكاتب" عند إضافة مقال.')
                    if specialist_profile is not None
                    else _("هذا الحساب غير مرتبط بملف أخصائي عام، فلا يمكن ضبط هذا الخيار له.")
                ),
            )

    def clean_email(self):
        email = self.cleaned_data["email"]
        queryset = User.objects.filter(email=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError(_("يوجد حساب بهذا البريد الإلكتروني بالفعل."))
        return email

    def clean_phone(self):
        # phone is unique=True, null=True — an empty string (rather than
        # NULL) would collide the moment a second admin is also left
        # blank, so normalize blank input to None like apps.accounts.forms
        # already does for the public profile-edit form.
        return self.cleaned_data.get("phone") or None

    def save(self, commit=True):
        is_create = self.instance.pk is None
        user = super().save(commit=False)
        user.username = user.email
        user.is_staff = True
        if is_create:
            user.role = "admin"
        new_password = self.cleaned_data.get("password")
        if new_password:
            user.set_password(new_password)
        elif is_create:
            user.set_password(get_random_string(32))
        if commit:
            user.save()
            group = self.cleaned_data.get("group")
            user.groups.clear()
            if group:
                user.groups.add(group)
            specialist_profile = getattr(user, "specialist_profile", None)
            if specialist_profile is not None and "can_write_articles" in self.cleaned_data:
                specialist_profile.can_write_articles = self.cleaned_data["can_write_articles"]
                specialist_profile.save(update_fields=["can_write_articles"])
        return user
