from django.contrib import admin

from .models import MatchResult, QuizQuestion, QuizResponse

admin.site.register(QuizQuestion)
admin.site.register(QuizResponse)
admin.site.register(MatchResult)
