from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "specialists/<int:pk>/",
        views.SpecialistReviewCreateView.as_view(),
        name="specialist-review",
    ),
    path("courses/<int:pk>/", views.CourseReviewCreateView.as_view(), name="course-review"),
    path("products/<int:pk>/", views.ProductReviewCreateView.as_view(), name="product-review"),
]
