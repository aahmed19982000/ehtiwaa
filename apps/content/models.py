from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image_extension, validate_image_size


class Category(TimeStampedModel):
    """Article categories, managed from the panel (apps.adminpanel) —
    replaces the free-text category field Article used to have."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Article(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    # Breadcrumb/category badge shown on the article.
    category = models.ForeignKey(
        "content.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
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
    cover_image = models.ImageField(
        upload_to="articles/",
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_image_size],
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    # SEO metadata — both optional, templates fall back to `title` when
    # blank rather than requiring these on every article.
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    # English counterparts — the panel can auto-fill these via machine
    # translation (see apps.adminpanel.services.translate_article_fields),
    # but they're plain editable fields, not synced automatically on every
    # save. Blank means "no English version yet"; templates.content fall
    # back to the Arabic fields when serving /en/.
    title_en = models.CharField(max_length=255, blank=True)
    body_en = models.TextField(blank=True)
    meta_title_en = models.CharField(max_length=255, blank=True)
    meta_description_en = models.CharField(max_length=300, blank=True)

    REVIEW_STATUS_CHOICES = [
        ("draft", "draft"),
        ("pending_review", "pending_review"),
        ("approved", "approved"),
        ("rejected", "rejected"),
    ]
    # Internal editorial workflow, separate from `is_published` (public
    # visibility). Writers without the `publish_article` permission can
    # only move an article to "pending_review"; only someone who holds
    # that permission can set is_published — see
    # apps.adminpanel.views.ArticleReviewApproveView.
    review_status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default="draft")
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_articles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_articles",
    )

    image_fields_to_compress = ["cover_image"]

    class Meta:
        permissions = [("publish_article", "Can publish articles directly")]

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
    thumbnail = models.ImageField(
        upload_to="videos/thumbnails/",
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_image_size],
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    # Manually curated homepage placement — the "فيديوهات تعليمية" section
    # falls back to the latest published videos when nothing is featured.
    is_featured = models.BooleanField(default=False)

    image_fields_to_compress = ["thumbnail"]

    def __str__(self):
        return self.title

    @property
    def duration_display(self):
        minutes, seconds = divmod(self.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"


class Testimonial(TimeStampedModel):
    author_name = models.CharField(max_length=150)
    author_title = models.CharField(max_length=150, blank=True)
    photo = models.ImageField(
        upload_to="testimonials/",
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_image_size],
    )
    quote = models.TextField()
    is_active = models.BooleanField(default=True)

    image_fields_to_compress = ["photo"]

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
    image = models.ImageField(
        upload_to="banners/", validators=[validate_image_extension, validate_image_size]
    )
    link_url = models.URLField(blank=True)
    placement = models.CharField(max_length=30, choices=PLACEMENT_CHOICES)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    image_fields_to_compress = ["image"]

    def __str__(self):
        return self.title or f"Banner<{self.pk}>"
