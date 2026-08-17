from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path(
        "specialists/pending/",
        views.PendingSpecialistListView.as_view(),
        name="pending-specialists",
    ),
    path(
        "specialists/<int:pk>/approve/",
        views.SpecialistApproveView.as_view(),
        name="specialist-approve",
    ),
    path(
        "specialists/<int:pk>/reject/",
        views.SpecialistRejectView.as_view(),
        name="specialist-reject",
    ),
]
