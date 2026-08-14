from django.db import models

from apps.core.models import TimeStampedModel


class Course(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        "specialists.Specialist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_published = models.BooleanField(default=False)
    cover_image = models.ImageField(upload_to="courses/covers/", null=True, blank=True)

    def __str__(self):
        return self.title


class Module(TimeStampedModel):
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.title


class Lesson(TimeStampedModel):
    module = models.ForeignKey("courses.Module", on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Enrollment(TimeStampedModel):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="enrollments"
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "course")]

    def __str__(self):
        return f"Enrollment<{self.user_id}->{self.course_id}>"


class Certificate(TimeStampedModel):
    enrollment = models.OneToOneField(
        "courses.Enrollment", on_delete=models.CASCADE, related_name="certificate"
    )
    certificate_number = models.CharField(max_length=100, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="certificates/", null=True, blank=True)

    def __str__(self):
        return self.certificate_number
