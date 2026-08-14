from django.contrib import admin

from .models import AnswerOption, Assessment, Attempt, Question

admin.site.register(Assessment)
admin.site.register(Question)
admin.site.register(AnswerOption)
admin.site.register(Attempt)
