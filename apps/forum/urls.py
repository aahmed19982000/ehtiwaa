from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.QuestionListView.as_view(), name="list"),
    path("ask/", views.AskQuestionView.as_view(), name="ask"),
    path("<int:pk>/", views.QuestionDetailView.as_view(), name="detail"),
    path("<int:pk>/answer/", views.PostAnswerView.as_view(), name="answer"),
    path("<int:pk>/report/", views.ReportQuestionView.as_view(), name="report-question"),
    path("answers/<int:pk>/accept/", views.AcceptAnswerView.as_view(), name="accept-answer"),
    path("answers/<int:pk>/helpful/", views.ToggleHelpfulView.as_view(), name="toggle-helpful"),
    path("answers/<int:pk>/report/", views.ReportAnswerView.as_view(), name="report-answer"),
]
