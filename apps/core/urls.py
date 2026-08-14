from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("terms/", views.TermsView.as_view(), name="terms"),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
]
