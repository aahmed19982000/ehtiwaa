from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView

from apps.dashboard.models import WishlistItem
from apps.payments.services import create_order_for_item
from apps.reviews.models import Review

from .models import Course, Enrollment, Lesson
from .services import mark_lesson_complete


def _attach_lock_state(modules, enrollment):
    """Mutates each prefetched Lesson with a transient `.locked` attribute —
    computed per-request from enrollment status, so it doesn't belong on the
    model itself."""
    for module in modules:
        unlocked = enrollment is not None or module.is_free_preview
        for lesson in module.lessons.all():
            lesson.locked = not unlocked


def _flatten_lessons(course):
    lessons = []
    for module in course.modules.all():
        lessons.extend(module.lessons.all())
    return lessons


class CourseListView(ListView):
    model = Course
    template_name = "courses/list.html"
    context_object_name = "courses"
    paginate_by = 12

    def get_queryset(self):
        return (
            Course.objects.filter(is_published=True)
            .select_related("instructor")
            .order_by("-created_at")
        )


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/detail.html"
    context_object_name = "course"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Course.objects.filter(is_published=True)
            .select_related("instructor")
            .prefetch_related("modules__lessons")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        user = self.request.user

        enrollment = None
        if user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=user, course=course).first()

        modules = list(course.modules.all())
        _attach_lock_state(modules, enrollment)

        content_type = ContentType.objects.get_for_model(Course)
        reviews = (
            Review.objects.filter(content_type=content_type, object_id=course.pk)
            .select_related("user")
            .order_by("-created_at")[:20]
        )

        first_lesson = next(iter(_flatten_lessons(course)), None)

        is_wishlisted = False
        if user.is_authenticated:
            is_wishlisted = WishlistItem.objects.filter(
                user=user, content_type=content_type, object_id=course.pk
            ).exists()

        instructor_stats = None
        if course.instructor:
            instructor_courses = Course.objects.filter(
                instructor=course.instructor, is_published=True
            )
            instructor_stats = {
                "courses_count": instructor_courses.count(),
                "students_count": Enrollment.objects.filter(course__in=instructor_courses)
                .values("user")
                .distinct()
                .count(),
            }

        related_courses = (
            Course.objects.filter(is_published=True)
            .exclude(pk=course.pk)
            .select_related("instructor")
        )
        if course.category:
            related_courses = related_courses.filter(category=course.category)
        related_courses = list(related_courses.order_by("-average_rating")[:4])
        if len(related_courses) < 4:
            fallback_ids = [c.pk for c in related_courses]
            fallback = (
                Course.objects.filter(is_published=True)
                .exclude(pk__in=[course.pk, *fallback_ids])
                .select_related("instructor")
                .order_by("-average_rating")[: 4 - len(related_courses)]
            )
            related_courses.extend(fallback)

        context.update(
            {
                "modules": modules,
                "enrollment": enrollment,
                "is_enrolled": enrollment is not None,
                "is_wishlisted": is_wishlisted,
                "reviews": reviews,
                "first_lesson": first_lesson,
                "instructor_stats": instructor_stats,
                "related_courses": related_courses,
            }
        )
        return context


class CourseCheckoutView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_published=True)
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            messages.info(request, _("أنت مسجّل بالفعل في هذه الدورة."))
            return redirect("courses:detail", slug=slug)

        order = create_order_for_item(request.user, course, course.price)
        return redirect("payments:checkout", order_id=order.pk)


class LessonDetailView(DetailView):
    model = Lesson
    template_name = "courses/lesson.html"
    context_object_name = "lesson"
    pk_url_kwarg = "lesson_id"

    def get_queryset(self):
        return Lesson.objects.filter(module__course__slug=self.kwargs["slug"]).select_related(
            "module__course"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lesson = self.object
        course = lesson.module.course
        user = self.request.user

        enrollment = None
        if user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=user, course=course).first()

        modules = list(course.modules.all())
        _attach_lock_state(modules, enrollment)

        lessons = _flatten_lessons(course)
        position = lessons.index(lesson) if lesson in lessons else -1
        next_lesson = lessons[position + 1] if 0 <= position < len(lessons) - 1 else None

        completed_lesson_ids = set()
        if enrollment:
            completed_lesson_ids = set(
                enrollment.lesson_progress.values_list("lesson_id", flat=True)
            )

        accessible = enrollment is not None or lesson.module.is_free_preview

        context.update(
            {
                "course": course,
                "modules": modules,
                "enrollment": enrollment,
                "accessible": accessible,
                "next_lesson": next_lesson,
                "is_completed": lesson.id in completed_lesson_ids,
            }
        )
        return context


class LessonCompleteView(LoginRequiredMixin, View):
    def post(self, request, slug, lesson_id):
        enrollment = get_object_or_404(Enrollment, user=request.user, course__slug=slug)
        lesson = get_object_or_404(Lesson, pk=lesson_id, module__course=enrollment.course)

        mark_lesson_complete(enrollment, lesson)
        if enrollment.completed_at:
            messages.success(request, _("مبروك! أتممت الدورة وحصلت على شهادة الإتمام."))
        else:
            messages.success(request, _("تم تسجيل تقدّمك في الدرس."))

        lessons = _flatten_lessons(enrollment.course)
        position = lessons.index(lesson) if lesson in lessons else -1
        next_lesson = lessons[position + 1] if 0 <= position < len(lessons) - 1 else None
        if next_lesson:
            return redirect("courses:lesson", slug=slug, lesson_id=next_lesson.pk)
        return redirect("courses:detail", slug=slug)


class CertificateDownloadView(LoginRequiredMixin, View):
    def get(self, request, slug):
        enrollment = get_object_or_404(
            Enrollment, user=request.user, course__slug=slug, completed_at__isnull=False
        )
        certificate = getattr(enrollment, "certificate", None)
        if not certificate or not certificate.file:
            raise Http404
        return FileResponse(
            certificate.file.open("rb"),
            as_attachment=True,
            filename=f"{certificate.certificate_number}.pdf",
        )
