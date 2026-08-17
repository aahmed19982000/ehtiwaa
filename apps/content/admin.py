from django.contrib import admin

from .models import Article, Banner, Testimonial, Video


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "is_published", "published_at"]
    list_editable = ["is_published"]
    list_filter = ["is_published", "category"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ["title"]}
    autocomplete_fields = ["author"]


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "duration_display", "views_count", "is_published"]
    list_editable = ["is_published"]
    list_filter = ["is_published", "category"]
    search_fields = ["title", "description"]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["author_name", "author_title", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["author_name", "quote"]


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["title", "placement", "is_active", "starts_at", "ends_at"]
    list_editable = ["is_active"]
    list_filter = ["placement", "is_active"]
