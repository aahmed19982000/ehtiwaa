from django.contrib import admin

from .models import WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["user", "content_object", "created_at"]
    list_filter = ["content_type"]
    search_fields = ["user__email"]
