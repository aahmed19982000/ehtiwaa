from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import TimeStampedModel


class Article(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    # Breadcrumb/category badge shown on the article — free text, same
    # simplification as courses.Course.category (no category catalog yet).
    category = models.CharField(max_length=100, blank=True)
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    # Authors are specialists (matches the report's "كاتب مرتبط بأخصائي"),
    # not arbitrary accounts.User — the reading page's author card links
    # straight to the specialist's public profile.
    author = models.ForeignKey(
        "specialists.Specialist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    # Stores HTML markup rendered with |safe in the template — admin-authored
    # trusted content, not user input. No WYSIWYG editor is wired up yet;
    # authors write/paste HTML directly in the admin textarea.
    body = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="articles/", null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def reading_time_minutes(self):
        word_count = len(self.body.split())
        return max(1, round(word_count / 200))


class Video(TimeStampedModel):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    thumbnail = models.ImageField(upload_to="videos/thumbnails/", null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @property
    def duration_display(self):
        minutes, seconds = divmod(self.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"


class Testimonial(TimeStampedModel):
    author_name = models.CharField(max_length=150)
    author_title = models.CharField(max_length=150, blank=True)
    photo = models.ImageField(upload_to="testimonials/", null=True, blank=True)
    quote = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.author_name


class Banner(TimeStampedModel):
    # The design has exactly two ad placements on the home page — the wide
    # gradient hero banner and the small partner-cards grid below the
    # stats section. Not a free-text field: rendering code keys off these.
    PLACEMENT_CHOICES = [
        ("home_hero", "البانر الرئيسي (الصفحة الرئيسية)"),
        ("home_small_grid", "شبكة الإعلانات الصغيرة (الصفحة الرئيسية)"),
    ]

    title = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to="banners/")
    link_url = models.URLField(blank=True)
    placement = models.CharField(max_length=30, choices=PLACEMENT_CHOICES)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title or f"Banner<{self.pk}>"
