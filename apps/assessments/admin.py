from django.contrib import admin

from .models import AnswerOption, Assessment, Attempt, Question, ScoreLevel


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 0


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


class ScoreLevelInline(admin.TabularInline):
    model = ScoreLevel
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "estimated_minutes", "questions_count", "is_published"]
    list_editable = ["is_published"]
    list_filter = ["is_published", "category"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [ScoreLevelInline, QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "assessment", "order"]
    list_editable = ["order"]
    list_filter = ["assessment"]
    inlines = [AnswerOptionInline]


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = [
        "assessment",
        "user",
        "session_key",
        "total_score",
        "result_level",
        "completed_at",
    ]
    list_filter = ["assessment", "result_level"]
    search_fields = ["user__email", "session_key"]
