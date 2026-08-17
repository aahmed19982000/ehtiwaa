from django.contrib import admin

from .models import Certificate, Course, Enrollment, Lesson, LessonProgress, Module


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "instructor", "price", "is_published", "average_rating"]
    list_editable = ["is_published", "average_rating"]
    list_filter = ["is_published", "category"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order", "is_free_preview"]
    list_editable = ["order", "is_free_preview"]
    list_filter = ["course"]
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ["title", "module", "order", "duration_minutes"]
    list_editable = ["order", "duration_minutes"]
    list_filter = ["module__course"]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "progress_percent", "completed_at", "source_order"]
    list_filter = ["course"]
    search_fields = ["user__email", "course__title"]


admin.site.register(Certificate)
admin.site.register(LessonProgress)
