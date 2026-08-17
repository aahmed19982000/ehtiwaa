from django.urls import path

from . import views

app_name = "assessments"

urlpatterns = [
    path("", views.AssessmentListView.as_view(), name="list"),
    path("<slug:slug>/start/", views.AssessmentStartView.as_view(), name="start"),
    path(
        "take/<uuid:token>/<int:question_number>/",
        views.AssessmentTakeView.as_view(),
        name="take",
    ),
    path("result/<uuid:token>/", views.AssessmentResultView.as_view(), name="result"),
]
