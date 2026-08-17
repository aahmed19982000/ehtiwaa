from django.contrib import admin

from .models import Answer, ContentReport, Question, Tag, Vote


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ["author", "body", "is_accepted"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "views_count", "is_closed", "created_at"]
    list_editable = ["is_closed"]
    list_filter = ["is_closed", "tags"]
    search_fields = ["title", "body", "author__email"]
    inlines = [AnswerInline]


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    """Basic moderation queue — "أدوات إشراف أساسية"."""

    list_display = ["content_object", "reporter", "status", "created_at"]
    list_editable = ["status"]
    list_filter = ["status", "content_type"]
    search_fields = ["reason", "reporter__email"]


admin.site.register(Tag)
admin.site.register(Vote)
