from django.urls import path

from . import views

app_name = "specialists"

urlpatterns = [
    # Public directory — this app is now mounted at /specialists/ (see
    # config/urls.py) so the directory gets the natural root path, and the
    # "join as a specialist" flow (still using the landing/apply/... names
    # templates already reference) moves under join/.
    path("", views.SpecialistDirectoryView.as_view(), name="directory"),
    path("<int:pk>/", views.SpecialistDetailView.as_view(), name="detail"),
    path("join/", views.SpecialistLandingView.as_view(), name="landing"),
    path("join/apply/", views.SpecialistApplyView.as_view(), name="apply"),
    path("join/apply/documents/", views.SpecialistDocumentsView.as_view(), name="apply-documents"),
    path("join/pending/", views.SpecialistApplyPendingView.as_view(), name="apply-pending"),
]
