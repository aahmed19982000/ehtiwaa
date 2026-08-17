from django.contrib import admin

from .models import MatchResult, MatchResultItem, QuizChoice, QuizQuestion, QuizResponse


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 0


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "order"]
    list_editable = ["order"]
    inlines = [QuizChoiceInline]


class MatchResultItemInline(admin.TabularInline):
    model = MatchResultItem
    extra = 0
    readonly_fields = ["specialist", "reason", "rank"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ["run_token", "user", "session_key", "recommended_specialty", "created_at"]
    list_filter = ["recommended_specialty"]
    search_fields = ["user__email", "session_key", "run_token"]
    inlines = [MatchResultItemInline]


admin.site.register(QuizResponse)
