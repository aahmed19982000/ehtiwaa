from django.db import models

from apps.core.models import TimeStampedModel


class Article(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    author = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    body = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="articles/", null=True, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class Video(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    thumbnail = models.ImageField(upload_to="videos/thumbnails/", null=True, blank=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Testimonial(TimeStampedModel):
    author_name = models.CharField(max_length=150)
    author_title = models.CharField(max_length=150, blank=True)
    photo = models.ImageField(upload_to="testimonials/", null=True, blank=True)
    quote = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.author_name


class Banner(TimeStampedModel):
    title = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to="banners/")
    link_url = models.URLField(blank=True)
    placement = models.CharField(max_length=50, blank=True)  # e.g. "home_hero", "sidebar"
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title or f"Banner<{self.pk}>"
