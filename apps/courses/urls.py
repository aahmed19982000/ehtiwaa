from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="list"),
    path("<slug:slug>/", views.CourseDetailView.as_view(), name="detail"),
    path("<slug:slug>/certificate/", views.CertificateDownloadView.as_view(), name="certificate"),
    path("<slug:slug>/checkout/", views.CourseCheckoutView.as_view(), name="checkout"),
    path(
        "<slug:slug>/lessons/<int:lesson_id>/",
        views.LessonDetailView.as_view(),
        name="lesson",
    ),
    path(
        "<slug:slug>/lessons/<int:lesson_id>/complete/",
        views.LessonCompleteView.as_view(),
        name="lesson-complete",
    ),
]
