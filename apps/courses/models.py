from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import TimeStampedModel


class Course(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    # Breadcrumb/category label shown above the title (e.g. "الصحة النفسية")
    # — free text rather than a FK since the design has no category catalog.
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        "specialists.Specialist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Pre-discount price shown struck through next to `price` — blank when
    # the course isn't discounted.
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    cover_image = models.ImageField(upload_to="courses/covers/", null=True, blank=True)
    # Intro/trailer video shown on the detail page above the curriculum,
    # separate from any individual lesson's video_url.
    intro_video_url = models.URLField(blank=True)
    learning_outcomes = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    # Recomputed automatically by apps.reviews' post_save/post_delete
    # signal whenever a Review targets this course.
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    # See apps/specialists/models.py Specialist.reviews for why this is
    # needed — without it, deleting a Course leaves orphaned Review rows.
    reviews = GenericRelation("reviews.Review", related_query_name="course")

    def __str__(self):
        return self.title

    @property
    def discount_percent(self):
        if not self.original_price or self.original_price <= self.price:
            return 0
        return round((1 - self.price / self.original_price) * 100)

    @property
    def total_lessons_count(self):
        return Lesson.objects.filter(module__course=self).count()


class Module(TimeStampedModel):
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    # Accessible without enrollment — matches the "مقفل" lock badge shown
    # per module in the design; unset modules require an active Enrollment.
    is_free_preview = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Lesson(TimeStampedModel):
    module = models.ForeignKey("courses.Module", on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Enrollment(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="enrollments"
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    # The order whose payment granted this enrollment — null for
    # admin-granted enrollments (e.g. comps, manual fixes).
    source_order = models.ForeignKey(
        "payments.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_enrollments",
    )

    class Meta:
        unique_together = [("user", "course")]

    def __str__(self):
        return f"Enrollment<{self.user_id}->{self.course_id}>"


class LessonProgress(TimeStampedModel):
    """One row per lesson a student has marked complete — Enrollment's
    progress_percent/completed_at are recomputed from these, so this is the
    source of truth for "تتبع تقدّم الطالب"."""

    enrollment = models.ForeignKey(
        "courses.Enrollment", on_delete=models.CASCADE, related_name="lesson_progress"
    )
    lesson = models.ForeignKey("courses.Lesson", on_delete=models.CASCADE, related_name="+")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("enrollment", "lesson")]

    def __str__(self):
        return f"LessonProgress<{self.enrollment_id}:{self.lesson_id}>"


class Certificate(TimeStampedModel):
    enrollment = models.OneToOneField(
        "courses.Enrollment", on_delete=models.CASCADE, related_name="certificate"
    )
    certificate_number = models.CharField(max_length=100, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="certificates/", null=True, blank=True)

    def __str__(self):
        return self.certificate_number
