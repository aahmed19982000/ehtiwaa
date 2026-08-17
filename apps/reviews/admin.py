from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "content_object", "rating", "created_at"]
    list_filter = ["rating", "content_type"]
    search_fields = ["user__email", "comment"]
