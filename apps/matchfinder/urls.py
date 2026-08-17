from django.urls import path

from . import views

app_name = "matchfinder"

urlpatterns = [
    path("", views.MatchFinderIntroView.as_view(), name="intro"),
    path("start/", views.MatchFinderStartView.as_view(), name="start"),
    path(
        "questions/<uuid:run_token>/<int:question_number>/",
        views.MatchFinderQuestionView.as_view(),
        name="question",
    ),
    path("results/<uuid:run_token>/", views.MatchFinderResultsView.as_view(), name="results"),
]
