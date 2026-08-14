from django.urls import path

from . import views

app_name = "specialists"

urlpatterns = [
    path("apply/", views.SpecialistApplyView.as_view(), name="apply"),
]
