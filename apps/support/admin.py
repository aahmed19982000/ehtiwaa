from django.contrib import admin

from .models import FAQItem, HelpCategory, KBArticle, SupportTicket


@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "icon", "order"]
    list_editable = ["icon", "order"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ["question", "category", "order"]
    list_editable = ["order"]
    list_filter = ["category"]
    search_fields = ["question", "answer"]


@admin.register(KBArticle)
class KBArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "is_published"]
    list_editable = ["is_published"]
    list_filter = ["is_published", "category"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "full_name", "email", "category", "status", "created_at"]
    list_editable = ["status"]
    list_filter = ["status", "category"]
    search_fields = ["subject", "full_name", "email", "body"]
