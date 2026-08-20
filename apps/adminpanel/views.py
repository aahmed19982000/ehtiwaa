from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count, ProtectedError, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.content.models import Article, Banner, Category, Testimonial, Video
from apps.core.images import compress_image_bytes
from apps.core.models import HomepageContent
from apps.core.validators import validate_image_extension, validate_image_size
from apps.courses.models import Course, Lesson, Module
from apps.payments.models import Payment
from apps.specialists.models import Specialist, SpecialtyTag

from .forms import (
    AdminForm,
    ArticleForm,
    BannerForm,
    CategoryForm,
    CourseForm,
    HomepageContentForm,
    LessonForm,
    ModuleForm,
    PanelLoginForm,
    ReportGenerateForm,
    ReviewDecisionForm,
    RoleForm,
    SpecialistCreateForm,
    SpecialistForm,
    SpecialtyTagForm,
    TestimonialForm,
    VideoForm,
)
from .models import Report
from .permissions import admin_eligible_users
from .services import (
    approve_specialist,
    create_specialist_account,
    generate_report,
    generate_unique_slug,
    reject_specialist,
    translate_article_fields,
)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Independent ops panel, separate from Django Admin — gated to any
    staff account. Uses its own local login (PanelLoginView), not the
    public site's Auth0-backed one."""

    login_url = "adminpanel:panel-login"

    def test_func(self):
        return self.request.user.is_staff


class PanelPermissionRequiredMixin(StaffRequiredMixin):
    """`is_staff` plus at least one permission from `required_perms`.
    `User.has_perm()` already returns True for superusers unconditionally
    (Django's ModelBackend), so no separate superuser check is needed here.
    Every panel section — Specialists, Courses, Articles, Payments, etc. —
    uses this with its own `required_perms`; roles (Groups) that grant
    those permissions are managed at /panel/roles/ (see RoleForm)."""

    required_perms = []

    def test_func(self):
        if not super().test_func():
            return False
        return any(self.request.user.has_perm(perm) for perm in self.required_perms)


class SuperuserRequiredMixin(StaffRequiredMixin):
    """Role management is deliberately kept outside the capability system
    below — a role that could grant itself role-management access would
    be a privilege-escalation hole. Superuser only, same as Django's own
    Group/Permission admin."""

    def test_func(self):
        return super().test_func() and self.request.user.is_superuser


class PanelContextMixin:
    """Injects the sidebar's active-tab state used to highlight the
    current section in templates/adminpanel/base.html."""

    active_nav = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) if hasattr(super(), "get_context_data") else dict(kwargs)
        context["active_nav"] = self.active_nav
        return context


class PanelLoginView(View):
    """Local email/password login for staff, independent of the public
    site's Auth0-backed apps.accounts.views.LoginView — the panel is a
    separate back office and shouldn't depend on an external identity
    provider to be reachable."""

    template_name = "adminpanel/login.html"

    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect("adminpanel:dashboard")
        return render(request, self.template_name, {"form": PanelLoginForm()})

    def post(self, request):
        form = PanelLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            if user is not None and user.is_staff:
                login(request, user)
                return redirect("adminpanel:dashboard")
            form.add_error(None, _("البريد الإلكتروني أو كلمة المرور غير صحيحة."))
        return render(request, self.template_name, {"form": form})


class PanelDeleteView(PanelContextMixin, PanelPermissionRequiredMixin, View):
    """Shared confirm-then-delete flow for every CRUD module below. A
    subclass sets `model`/`success_url_name`/`required_perms`, optionally
    overrides `get_queryset()` (object-level scoping — see CourseDeleteView),
    `label_for()` (defaults to `str(obj)`), `extra_warning()` (e.g. an
    enrollment count) and `protected_message` for FK-protected deletes."""

    model = None
    success_url_name = ""
    protected_message = _("لا يمكن الحذف لوجود بيانات مرتبطة بهذا العنصر.")

    def get_queryset(self):
        return self.model.objects.all()

    def label_for(self, obj):
        return str(obj)

    def extra_warning(self, obj):
        return None

    def get_success_url(self, obj):
        """Override for a redirect target that needs args (e.g. back to a
        parent object's page) — defaults to the static success_url_name."""
        return self.success_url_name

    def get(self, request, pk):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        context = self.get_context_data(
            object_label=self.label_for(obj), extra_warning=self.extra_warning(obj)
        )
        return render(request, "adminpanel/panel_confirm_delete.html", context)

    def post(self, request, pk):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        success_url = self.get_success_url(obj)
        try:
            obj.delete()
            messages.success(request, _("تم الحذف بنجاح."))
        except ProtectedError:
            messages.error(request, self.protected_message)
        return redirect(success_url)


class ToggleFeaturedView(PanelPermissionRequiredMixin, View):
    model = None
    success_url_name = ""

    def get_queryset(self):
        return self.model.objects.all()

    def post(self, request, pk):
        obj = get_object_or_404(self.get_queryset(), pk=pk)
        obj.is_featured = not obj.is_featured
        obj.save(update_fields=["is_featured"])
        return redirect(self.success_url_name)


def _is_restricted_to_own_courses(user):
    """True only for a genuinely-restricted, non-superuser account holding
    `courses.manage_own_courses_only`. `is_superuser` is checked explicitly
    here rather than left to has_perm()'s usual bypass, because this is a
    *restriction* flag, not a capability grant — has_perm() returns True
    for literally any permission string once is_superuser is set, which
    would wrongly "restrict" superusers (who have no specialist profile)
    down to seeing/managing zero courses."""

    return not user.is_superuser and user.has_perm("courses.manage_own_courses_only")


def _scope_courses_to_instructor(queryset, user):
    """Course-instructor roles get `courses.manage_own_courses_only` (see
    apps.adminpanel.permissions.PANEL_CAPABILITIES) — when present, every
    course view is scoped to courses where the user's own specialist
    profile is the instructor, never falling back to "see everything"."""

    if not _is_restricted_to_own_courses(user):
        return queryset
    specialist_profile = getattr(user, "specialist_profile", None)
    if specialist_profile is None:
        return queryset.none()
    return queryset.filter(instructor=specialist_profile)


def _apply_article_workflow(request, form, *, is_create):
    """Shared publish/review branching for ArticleCreateView/UpdateView's
    form_valid. A user with `content.publish_article` behaves exactly like
    before (the "منشور" toggle drives is_published directly). Anyone else
    never has `is_published` in their form at all (popped in get_form), so
    Django's ModelForm simply never touches it — it stays at the model
    default (False) on create, and untouched on update, so editing an
    already-published article can never silently unpublish it."""

    article = form.instance
    if is_create:
        article.created_by = request.user

    if request.user.has_perm("content.publish_article"):
        if article.is_published:
            article.review_status = "approved"
            if not article.published_at:
                article.published_at = timezone.now()
    elif not article.is_published and request.POST.get("action") == "submit_review":
        article.review_status = "pending_review"


def _article_workflow_message(article, *, is_create):
    if article.review_status == "pending_review":
        return _("تم حفظ المقال وإرساله للمراجعة.")
    if article.is_published:
        return _("تمت إضافة المقال ونشره.") if is_create else _("تم تحديث المقال.")
    return _("تمت إضافة المقال كمسودة.") if is_create else _("تم تحديث المقال (لا يزال كمسودة).")


class DashboardOverviewView(PanelContextMixin, StaffRequiredMixin, TemplateView):
    active_nav = "dashboard"
    template_name = "adminpanel/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()
        month_start = today.replace(day=1)
        week_ago = timezone.now() - timedelta(days=7)

        context["payments_this_month"] = (
            (
                Payment.objects.filter(status="succeeded", paid_at__date__gte=month_start).aggregate(
                    total=Sum("order__total")
                )["total"]
                or 0
            )
            if user.has_perm("payments.view_order")
            else None
        )
        context["pending_specialists_count"] = (
            Specialist.objects.filter(status="pending").count()
            if user.has_perm("specialists.view_specialist")
            else None
        )
        context["bookings_today_count"] = (
            Booking.objects.filter(scheduled_start__date=today).count()
            if user.has_perm("bookings.view_booking")
            else None
        )
        context["new_users_week_count"] = (
            User.objects.filter(date_joined__gte=week_ago).count()
            if user.has_perm("accounts.view_user")
            else None
        )
        context["pending_articles_count"] = (
            Article.objects.filter(review_status="pending_review").count()
            if user.has_perm("content.publish_article")
            else None
        )
        return context


# --- Specialists ------------------------------------------------------


class SpecialistListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Specialist
    template_name = "adminpanel/specialists.html"
    context_object_name = "specialists"
    active_nav = "specialists"
    required_perms = ["specialists.view_specialist"]
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Specialist.objects.select_related("user", "user__profile")
            .prefetch_related("credential_documents")
            .order_by("-created_at")
        )
        status = self.request.GET.get("status")
        if status in dict(Specialist.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(full_name_ar__icontains=query)
                | Q(full_name_en__icontains=query)
                | Q(user__email__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Specialist.STATUS_CHOICES
        context["selected_status"] = self.request.GET.get("status", "")
        context["query"] = self.request.GET.get("q", "")
        counts = dict(
            Specialist.objects.values_list("status").annotate(count=Count("id"))
        )
        context["status_summary"] = [
            (value, label, counts.get(value, 0)) for value, label in Specialist.STATUS_CHOICES
        ]
        context["total_specialists_count"] = sum(counts.values())
        return context


class SpecialistApproveView(PanelPermissionRequiredMixin, View):
    required_perms = ["specialists.change_specialist"]

    def post(self, request, pk):
        specialist = get_object_or_404(Specialist, pk=pk, status="pending")
        form = ReviewDecisionForm(request.POST)
        notes = form.cleaned_data["notes"] if form.is_valid() else ""
        approve_specialist(specialist, request.user, notes)
        messages.success(request, _("تم اعتماد الأخصائي."))
        return redirect("adminpanel:specialists")


class SpecialistRejectView(PanelPermissionRequiredMixin, View):
    required_perms = ["specialists.change_specialist"]

    def post(self, request, pk):
        specialist = get_object_or_404(Specialist, pk=pk, status="pending")
        form = ReviewDecisionForm(request.POST)
        notes = form.cleaned_data["notes"] if form.is_valid() else ""
        reject_specialist(specialist, request.user, notes)
        messages.success(request, _("تم رفض الطلب."))
        return redirect("adminpanel:specialists")


class SpecialistCreateView(PanelContextMixin, PanelPermissionRequiredMixin, View):
    template_name = "adminpanel/panel_form.html"
    active_nav = "specialists"
    required_perms = ["specialists.add_specialist"]

    def get(self, request):
        context = self.get_context_data(form=SpecialistCreateForm(), title=_("إضافة أخصائي"), is_multipart=False)
        return render(request, self.template_name, context)

    def post(self, request):
        form = SpecialistCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data.copy()
            email = data.pop("email")
            create_specialist_account(email, data)
            messages.success(
                request,
                _(
                    'تم إنشاء حساب الأخصائي. وجّهه لاستخدام "نسيت كلمة المرور" '
                    "بنفس البريد الإلكتروني لتفعيل حسابه."
                ),
            )
            return redirect("adminpanel:specialists")
        context = self.get_context_data(form=form, title=_("إضافة أخصائي"), is_multipart=False)
        return render(request, self.template_name, context)


class SpecialistUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Specialist
    form_class = SpecialistForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "specialists"
    required_perms = ["specialists.change_specialist"]
    success_url = reverse_lazy("adminpanel:specialists")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل بيانات الأخصائي")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث بيانات الأخصائي."))
        return super().form_valid(form)


class SpecialistDeleteView(PanelDeleteView):
    model = Specialist
    success_url_name = "adminpanel:specialists"
    active_nav = "specialists"
    required_perms = ["specialists.delete_specialist"]
    protected_message = _(
        "لا يمكن حذف هذا الأخصائي لوجود حجوزات مرتبطة به. يمكنك تعليق حسابه "
        '(تغيير الحالة إلى "موقوف") بدلاً من ذلك.'
    )

    def label_for(self, obj):
        return obj.full_name_ar or obj.full_name_en or obj.user.email


class SpecialistToggleFeaturedView(ToggleFeaturedView):
    model = Specialist
    success_url_name = "adminpanel:specialists"
    required_perms = ["specialists.change_specialist"]


# --- Courses ------------------------------------------------------


class CourseListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Course
    template_name = "adminpanel/courses.html"
    context_object_name = "courses"
    active_nav = "courses"
    required_perms = ["courses.view_course"]
    paginate_by = 25

    def get_queryset(self):
        queryset = Course.objects.select_related("instructor").order_by("-created_at")
        return _scope_courses_to_instructor(queryset, self.request.user)


class CourseCreateView(PanelContextMixin, PanelPermissionRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "courses"
    required_perms = ["courses.add_course"]
    success_url = reverse_lazy("adminpanel:courses")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if _is_restricted_to_own_courses(self.request.user):
            form.fields.pop("instructor", None)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة دورة")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        if not form.cleaned_data.get("slug"):
            form.instance.slug = generate_unique_slug(Course, form.cleaned_data["title"], fallback="course")
        if _is_restricted_to_own_courses(self.request.user):
            form.instance.instructor = getattr(self.request.user, "specialist_profile", None)
        messages.success(self.request, _("تمت إضافة الدورة."))
        return super().form_valid(form)


class CourseUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "courses"
    required_perms = ["courses.change_course"]
    success_url = reverse_lazy("adminpanel:courses")

    def get_queryset(self):
        return _scope_courses_to_instructor(Course.objects.all(), self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if _is_restricted_to_own_courses(self.request.user):
            form.fields.pop("instructor", None)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل الدورة")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        if not form.cleaned_data.get("slug"):
            form.instance.slug = generate_unique_slug(Course, form.cleaned_data["title"], fallback="course")
        messages.success(self.request, _("تم تحديث الدورة."))
        return super().form_valid(form)


class CourseDeleteView(PanelDeleteView):
    model = Course
    success_url_name = "adminpanel:courses"
    active_nav = "courses"
    required_perms = ["courses.delete_course"]

    def get_queryset(self):
        return _scope_courses_to_instructor(Course.objects.all(), self.request.user)

    def label_for(self, obj):
        return obj.title

    def extra_warning(self, obj):
        count = obj.enrollments.count()
        if count:
            return _("سيتم حذف %(count)d تسجيل طالب مرتبط بهذه الدورة أيضًا.") % {"count": count}
        return None


class CourseToggleFeaturedView(ToggleFeaturedView):
    model = Course
    success_url_name = "adminpanel:courses"
    required_perms = ["courses.change_course"]

    def get_queryset(self):
        return _scope_courses_to_instructor(Course.objects.all(), self.request.user)


# --- Course curriculum: modules + lessons ------------------------------
# Gated on courses.change_course (same as editing the course itself) rather
# than dedicated Module/Lesson permissions — there's no panel role UI for
# those, and "can edit this course" already implies "can edit its content".


class CourseCurriculumView(PanelContextMixin, PanelPermissionRequiredMixin, DetailView):
    model = Course
    template_name = "adminpanel/course_curriculum.html"
    context_object_name = "course"
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def get_queryset(self):
        return _scope_courses_to_instructor(Course.objects.all(), self.request.user).prefetch_related(
            "modules__lessons"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["module_form"] = ModuleForm()
        context["lesson_form"] = LessonForm()
        return context


class ModuleCreateView(PanelPermissionRequiredMixin, View):
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def post(self, request, pk):
        course = get_object_or_404(
            _scope_courses_to_instructor(Course.objects.all(), request.user), pk=pk
        )
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, _("تمت إضافة الوحدة."))
        else:
            errors = " ".join(error for field_errors in form.errors.values() for error in field_errors)
            messages.error(request, errors or _("تعذّرت إضافة الوحدة."))
        return redirect("adminpanel:course-curriculum", pk=course.pk)


class ModuleUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def get_queryset(self):
        return Module.objects.filter(
            course__in=_scope_courses_to_instructor(Course.objects.all(), self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل الوحدة")
        return context

    def get_success_url(self):
        return reverse("adminpanel:course-curriculum", args=[self.object.course_id])

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الوحدة."))
        return super().form_valid(form)


class ModuleDeleteView(PanelDeleteView):
    model = Module
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def get_queryset(self):
        return Module.objects.filter(
            course__in=_scope_courses_to_instructor(Course.objects.all(), self.request.user)
        )

    def label_for(self, obj):
        return obj.title

    def extra_warning(self, obj):
        count = obj.lessons.count()
        if count:
            return _("سيتم حذف %(count)d درس مرتبط بهذه الوحدة أيضًا.") % {"count": count}
        return None

    def get_success_url(self, obj):
        return reverse("adminpanel:course-curriculum", args=[obj.course_id])


class LessonCreateView(PanelPermissionRequiredMixin, View):
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def post(self, request, pk):
        module = get_object_or_404(
            Module.objects.filter(
                course__in=_scope_courses_to_instructor(Course.objects.all(), request.user)
            ),
            pk=pk,
        )
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.save()
            messages.success(request, _("تمت إضافة الدرس."))
        else:
            errors = " ".join(error for field_errors in form.errors.values() for error in field_errors)
            messages.error(request, errors or _("تعذّرت إضافة الدرس."))
        return redirect("adminpanel:course-curriculum", pk=module.course_id)


class LessonUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def get_queryset(self):
        return Lesson.objects.filter(
            module__course__in=_scope_courses_to_instructor(Course.objects.all(), self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل الدرس")
        return context

    def get_success_url(self):
        return reverse("adminpanel:course-curriculum", args=[self.object.module.course_id])

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الدرس."))
        return super().form_valid(form)


class LessonDeleteView(PanelDeleteView):
    model = Lesson
    active_nav = "courses"
    required_perms = ["courses.change_course"]

    def get_queryset(self):
        return Lesson.objects.filter(
            module__course__in=_scope_courses_to_instructor(Course.objects.all(), self.request.user)
        )

    def label_for(self, obj):
        return obj.title

    def get_success_url(self, obj):
        return reverse("adminpanel:course-curriculum", args=[obj.module.course_id])


# --- Articles ------------------------------------------------------


class ArticleListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Article
    template_name = "adminpanel/articles.html"
    context_object_name = "articles"
    active_nav = "articles"
    required_perms = ["content.view_article"]
    paginate_by = 25

    def get_queryset(self):
        return Article.objects.select_related("author").order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.has_perm("content.publish_article"):
            context["pending_review_articles"] = Article.objects.filter(
                review_status="pending_review"
            ).select_related("author", "created_by")
        return context


class ArticleCreateView(PanelContextMixin, PanelPermissionRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = "adminpanel/article_form.html"
    active_nav = "articles"
    required_perms = ["content.add_article"]
    success_url = reverse_lazy("adminpanel:articles")

    def get_initial(self):
        initial = super().get_initial()
        # Staff who are also specialists usually write as themselves —
        # pre-select their own profile, still fully changeable in the form.
        specialist_profile = getattr(self.request.user, "specialist_profile", None)
        if specialist_profile is not None:
            initial["author"] = specialist_profile.pk
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.request.user.has_perm("content.publish_article"):
            form.fields.pop("is_published", None)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة مقال")
        context["is_multipart"] = True
        context["can_publish"] = self.request.user.has_perm("content.publish_article")
        context["has_available_authors"] = Specialist.objects.filter(can_write_articles=True).exists()
        return context

    def form_valid(self, form):
        if not form.cleaned_data.get("slug"):
            form.instance.slug = generate_unique_slug(Article, form.cleaned_data["title"], fallback="article")
        _apply_article_workflow(self.request, form, is_create=True)
        messages.success(self.request, _article_workflow_message(form.instance, is_create=True))
        return super().form_valid(form)


class ArticleUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = "adminpanel/article_form.html"
    active_nav = "articles"
    required_perms = ["content.change_article"]
    success_url = reverse_lazy("adminpanel:articles")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.request.user.has_perm("content.publish_article"):
            form.fields.pop("is_published", None)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل المقال")
        context["is_multipart"] = True
        context["can_publish"] = self.request.user.has_perm("content.publish_article")
        context["has_available_authors"] = Specialist.objects.filter(can_write_articles=True).exists()
        return context

    def form_valid(self, form):
        if not form.cleaned_data.get("slug"):
            form.instance.slug = generate_unique_slug(Article, form.cleaned_data["title"], fallback="article")
        _apply_article_workflow(self.request, form, is_create=False)
        messages.success(self.request, _article_workflow_message(form.instance, is_create=False))
        return super().form_valid(form)


class ArticleDeleteView(PanelDeleteView):
    model = Article
    success_url_name = "adminpanel:articles"
    active_nav = "articles"
    required_perms = ["content.delete_article"]

    def label_for(self, obj):
        return obj.title


class ArticleReviewApproveView(PanelPermissionRequiredMixin, View):
    required_perms = ["content.publish_article"]

    def post(self, request, pk):
        article = get_object_or_404(Article, pk=pk, review_status="pending_review")
        article.is_published = True
        article.review_status = "approved"
        article.reviewed_by = request.user
        article.reviewed_at = timezone.now()
        if not article.published_at:
            article.published_at = timezone.now()
        article.save(
            update_fields=["is_published", "review_status", "reviewed_by", "reviewed_at", "published_at"]
        )
        messages.success(request, _("تم اعتماد المقال ونشره."))
        return redirect("adminpanel:articles")


class ArticleReviewRejectView(PanelPermissionRequiredMixin, View):
    required_perms = ["content.publish_article"]

    def post(self, request, pk):
        article = get_object_or_404(Article, pk=pk, review_status="pending_review")
        form = ReviewDecisionForm(request.POST)
        notes = form.cleaned_data["notes"] if form.is_valid() else ""
        article.review_status = "rejected"
        article.review_notes = notes
        article.reviewed_by = request.user
        article.reviewed_at = timezone.now()
        article.save(update_fields=["review_status", "review_notes", "reviewed_by", "reviewed_at"])
        messages.success(request, _("تم رفض المقال."))
        return redirect("adminpanel:articles")


class ArticleImageUploadView(PanelPermissionRequiredMixin, View):
    """Backs the article body editor's image button (templates/adminpanel/
    article_form.html) — validates and stores an upload the same way
    Article.cover_image does, and hands back a URL to insert inline."""

    required_perms = ["content.add_article", "content.change_article"]

    def post(self, request):
        uploaded_file = request.FILES.get("image")
        if uploaded_file is None:
            return JsonResponse({"error": _("لم يتم اختيار ملف.")}, status=400)
        try:
            validate_image_extension(uploaded_file)
            validate_image_size(uploaded_file)
        except ValidationError as exc:
            return JsonResponse({"error": " ".join(exc.messages)}, status=400)

        # Saved straight to storage, not through a model field, so it
        # doesn't get TimeStampedModel.save()'s automatic compression —
        # apply it directly here instead.
        compressed = compress_image_bytes(uploaded_file)
        content = ContentFile(compressed) if compressed is not None else uploaded_file
        path = default_storage.save(f"articles/body-images/{uploaded_file.name}", content)
        return JsonResponse({"url": default_storage.url(path)})


class ArticleTranslateView(PanelPermissionRequiredMixin, View):
    """Backs the article form's "ترجمة تلقائية" button — best-effort
    Arabic→English machine translation of the currently-typed field
    values (not yet saved), returned for staff to review/edit before
    submitting the form."""

    required_perms = ["content.add_article", "content.change_article"]

    def post(self, request):
        translated = translate_article_fields(
            request.POST.get("title", ""),
            request.POST.get("body", ""),
            request.POST.get("meta_title", ""),
            request.POST.get("meta_description", ""),
        )
        return JsonResponse(translated)


class CategoryListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Category
    template_name = "adminpanel/categories.html"
    context_object_name = "categories"
    active_nav = "articles"
    required_perms = ["content.view_category"]

    def get_queryset(self):
        return Category.objects.order_by("name")


class CategoryCreateView(PanelContextMixin, PanelPermissionRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "articles"
    required_perms = ["content.add_category"]
    success_url = reverse_lazy("adminpanel:categories")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة تصنيف")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تمت إضافة التصنيف."))
        return super().form_valid(form)


class CategoryUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "articles"
    required_perms = ["content.change_category"]
    success_url = reverse_lazy("adminpanel:categories")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل التصنيف")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث التصنيف."))
        return super().form_valid(form)


class CategoryDeleteView(PanelDeleteView):
    model = Category
    success_url_name = "adminpanel:categories"
    active_nav = "articles"
    required_perms = ["content.delete_category"]

    def label_for(self, obj):
        return obj.name


# --- Videos ------------------------------------------------------


class VideoListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Video
    template_name = "adminpanel/videos.html"
    context_object_name = "videos"
    active_nav = "videos"
    required_perms = ["content.view_video"]
    paginate_by = 25

    def get_queryset(self):
        return Video.objects.order_by("-created_at")


class VideoCreateView(PanelContextMixin, PanelPermissionRequiredMixin, CreateView):
    model = Video
    form_class = VideoForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "videos"
    required_perms = ["content.add_video"]
    success_url = reverse_lazy("adminpanel:videos")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة فيديو")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تمت إضافة الفيديو."))
        return super().form_valid(form)


class VideoUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Video
    form_class = VideoForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "videos"
    required_perms = ["content.change_video"]
    success_url = reverse_lazy("adminpanel:videos")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل الفيديو")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الفيديو."))
        return super().form_valid(form)


class VideoDeleteView(PanelDeleteView):
    model = Video
    success_url_name = "adminpanel:videos"
    active_nav = "videos"
    required_perms = ["content.delete_video"]

    def label_for(self, obj):
        return obj.title


class VideoToggleFeaturedView(ToggleFeaturedView):
    model = Video
    success_url_name = "adminpanel:videos"
    required_perms = ["content.change_video"]


# --- Homepage: hero content, banners, testimonials --------------------


class HomepageContentView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = HomepageContent
    form_class = HomepageContentForm
    template_name = "adminpanel/homepage.html"
    active_nav = "homepage"
    required_perms = ["core.change_homepagecontent"]
    success_url = reverse_lazy("adminpanel:homepage")

    def get_object(self, queryset=None):
        return HomepageContent.objects.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["banners"] = Banner.objects.order_by("-created_at")[:10]
        context["testimonials"] = Testimonial.objects.order_by("-created_at")[:10]
        context["specialty_tags"] = SpecialtyTag.objects.order_by("name")
        context.setdefault("specialty_tag_form", SpecialtyTagForm())
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث محتوى الصفحة الرئيسية."))
        return super().form_valid(form)


class SpecialtyTagCreateView(PanelPermissionRequiredMixin, View):
    active_nav = "homepage"
    required_perms = ["core.change_homepagecontent"]

    def post(self, request):
        form = SpecialtyTagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("تمت إضافة التصنيف."))
        else:
            errors = " ".join(error for field_errors in form.errors.values() for error in field_errors)
            messages.error(request, errors or _("تعذّرت إضافة التصنيف."))
        return redirect("adminpanel:homepage")


class SpecialtyTagDeleteView(PanelDeleteView):
    model = SpecialtyTag
    success_url_name = "adminpanel:homepage"
    active_nav = "homepage"
    required_perms = ["core.change_homepagecontent"]

    def label_for(self, obj):
        return obj.name


class BannerListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Banner
    template_name = "adminpanel/banners.html"
    context_object_name = "banners"
    active_nav = "homepage"
    required_perms = ["content.view_banner"]

    def get_queryset(self):
        return Banner.objects.order_by("-created_at")


class BannerCreateView(PanelContextMixin, PanelPermissionRequiredMixin, CreateView):
    model = Banner
    form_class = BannerForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "homepage"
    required_perms = ["content.add_banner"]
    success_url = reverse_lazy("adminpanel:banners")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة بانر")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تمت إضافة البانر."))
        return super().form_valid(form)


class BannerUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Banner
    form_class = BannerForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "homepage"
    required_perms = ["content.change_banner"]
    success_url = reverse_lazy("adminpanel:banners")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل البانر")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث البانر."))
        return super().form_valid(form)


class BannerDeleteView(PanelDeleteView):
    model = Banner
    success_url_name = "adminpanel:banners"
    active_nav = "homepage"
    required_perms = ["content.delete_banner"]

    def label_for(self, obj):
        return obj.title or f"بانر #{obj.pk}"


class TestimonialListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Testimonial
    template_name = "adminpanel/testimonials.html"
    context_object_name = "testimonials"
    active_nav = "homepage"
    required_perms = ["content.view_testimonial"]

    def get_queryset(self):
        return Testimonial.objects.order_by("-created_at")


class TestimonialCreateView(PanelContextMixin, PanelPermissionRequiredMixin, CreateView):
    model = Testimonial
    form_class = TestimonialForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "homepage"
    required_perms = ["content.add_testimonial"]
    success_url = reverse_lazy("adminpanel:testimonials")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة رأي")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تمت الإضافة."))
        return super().form_valid(form)


class TestimonialUpdateView(PanelContextMixin, PanelPermissionRequiredMixin, UpdateView):
    model = Testimonial
    form_class = TestimonialForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "homepage"
    required_perms = ["content.change_testimonial"]
    success_url = reverse_lazy("adminpanel:testimonials")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل الرأي")
        context["is_multipart"] = True
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم التحديث."))
        return super().form_valid(form)


class TestimonialDeleteView(PanelDeleteView):
    model = Testimonial
    success_url_name = "adminpanel:testimonials"
    active_nav = "homepage"
    required_perms = ["content.delete_testimonial"]

    def label_for(self, obj):
        return obj.author_name


# --- Users / Bookings / Payments / Reports -----------------------------


class PaymentsListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Payment
    template_name = "adminpanel/payments.html"
    context_object_name = "payments"
    paginate_by = 25
    active_nav = "payments"
    required_perms = ["payments.view_order"]

    def get_queryset(self):
        queryset = Payment.objects.select_related("order", "order__user").order_by("-created_at")
        status = self.request.GET.get("status")
        if status in dict(Payment.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Payment.STATUS_CHOICES
        context["selected_status"] = self.request.GET.get("status", "")
        return context


class UsersListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = User
    template_name = "adminpanel/users.html"
    context_object_name = "users"
    paginate_by = 25
    active_nav = "users"
    required_perms = ["accounts.view_user"]

    def get_queryset(self):
        queryset = User.objects.order_by("-date_joined")
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(email__icontains=query) | Q(phone__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        return context


class BookingsListView(PanelContextMixin, PanelPermissionRequiredMixin, ListView):
    model = Booking
    template_name = "adminpanel/bookings.html"
    context_object_name = "bookings"
    paginate_by = 25
    active_nav = "bookings"
    required_perms = ["bookings.view_booking"]

    def get_queryset(self):
        queryset = Booking.objects.select_related("client", "specialist").order_by("-scheduled_start")
        status = self.request.GET.get("status")
        if status in dict(Booking.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Booking.STATUS_CHOICES
        context["selected_status"] = self.request.GET.get("status", "")
        return context


class ReportsView(PanelContextMixin, PanelPermissionRequiredMixin, View):
    active_nav = "reports"
    template_name = "adminpanel/reports.html"
    required_perms = ["adminpanel.view_report"]

    def get(self, request):
        context = self.get_context_data(
            reports=Report.objects.select_related("generated_by").order_by("-created_at")[:50],
            form=ReportGenerateForm(),
        )
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.has_perm("adminpanel.add_report"):
            messages.error(request, _("لا تملك صلاحية إنشاء تقارير."))
            return redirect("adminpanel:reports")

        form = ReportGenerateForm(request.POST)
        if form.is_valid():
            generate_report(
                form.cleaned_data["report_type"],
                form.cleaned_data["date_from"],
                form.cleaned_data["date_to"],
                request.user,
            )
            messages.success(request, _("تم إنشاء التقرير."))
            return redirect("adminpanel:reports")

        context = self.get_context_data(
            reports=Report.objects.select_related("generated_by").order_by("-created_at")[:50],
            form=form,
        )
        return render(request, self.template_name, context)


# --- Roles & permissions (superuser only) ------------------------------


class RoleListView(PanelContextMixin, SuperuserRequiredMixin, ListView):
    model = Group
    template_name = "adminpanel/roles.html"
    context_object_name = "roles"
    active_nav = "roles"

    def get_queryset(self):
        return Group.objects.annotate(member_count=Count("user")).order_by("name")


class RoleCreateView(PanelContextMixin, SuperuserRequiredMixin, CreateView):
    model = Group
    form_class = RoleForm
    template_name = "adminpanel/role_form.html"
    active_nav = "roles"
    success_url = reverse_lazy("adminpanel:roles")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة دور")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم إنشاء الدور."))
        return super().form_valid(form)


class RoleUpdateView(PanelContextMixin, SuperuserRequiredMixin, UpdateView):
    model = Group
    form_class = RoleForm
    template_name = "adminpanel/role_form.html"
    active_nav = "roles"
    success_url = reverse_lazy("adminpanel:roles")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل الدور")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث الدور."))
        return super().form_valid(form)


class RoleDeleteView(PanelContextMixin, SuperuserRequiredMixin, View):
    active_nav = "roles"

    def get(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        context = self.get_context_data(object_label=group.name, extra_warning=None)
        return render(request, "adminpanel/panel_confirm_delete.html", context)

    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        group.delete()
        messages.success(request, _("تم حذف الدور."))
        return redirect("adminpanel:roles")


class AdminsListView(PanelContextMixin, SuperuserRequiredMixin, ListView):
    """Every admin-eligible account (apps.adminpanel.permissions.
    admin_eligible_users — never ordinary clients) with its current
    role(s) and an inline reassign control, plus the entry point for
    creating a brand-new admin account."""

    model = User
    template_name = "adminpanel/admins.html"
    context_object_name = "admin_users"
    active_nav = "roles"

    def get_queryset(self):
        return admin_eligible_users().prefetch_related("groups")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = Group.objects.order_by("name")
        return context


class AdminAssignRoleView(SuperuserRequiredMixin, View):
    """Backs the Admins list's inline quick-reassign dropdown — the full
    AdminUpdateView below covers the same ground plus everything else, but
    this stays for one-click role changes without leaving the list."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        group = Group.objects.filter(pk=request.POST.get("group")).first()
        user.groups.clear()
        if group:
            user.groups.add(group)
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        messages.success(request, _("تم تحديث دور المستخدم."))
        return redirect("adminpanel:admins")


class AdminCreateView(PanelContextMixin, SuperuserRequiredMixin, CreateView):
    model = User
    form_class = AdminForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "roles"
    success_url = reverse_lazy("adminpanel:admins")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("إضافة أدمن")
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            _(
                'تم إنشاء حساب الأدمن. لو ماحددتش كلمة مرور، وجّهه لاستخدام '
                '"نسيت كلمة المرور" بنفس البريد الإلكتروني لتفعيل حسابه.'
            ),
        )
        return super().form_valid(form)


class AdminUpdateView(PanelContextMixin, SuperuserRequiredMixin, UpdateView):
    model = User
    form_class = AdminForm
    template_name = "adminpanel/panel_form.html"
    active_nav = "roles"
    success_url = reverse_lazy("adminpanel:admins")

    def get_queryset(self):
        return admin_eligible_users()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("تعديل بيانات الأدمن")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("تم تحديث بيانات الأدمن."))
        return super().form_valid(form)
