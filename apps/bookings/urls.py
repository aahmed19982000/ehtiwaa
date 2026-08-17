from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.BookingListView.as_view(), name="list"),
    path("<int:pk>/", views.BookingDetailView.as_view(), name="detail"),
    path("<int:pk>/cancel/", views.BookingCancelView.as_view(), name="cancel"),
    path("book/<int:specialist_pk>/", views.BookingCreateView.as_view(), name="create"),
]
