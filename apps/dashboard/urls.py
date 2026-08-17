from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardBookingsView.as_view(), name="index"),
    path("bookings/", views.DashboardBookingsView.as_view(), name="bookings"),
    path("courses/", views.DashboardCoursesView.as_view(), name="courses"),
    path("orders/", views.DashboardOrdersView.as_view(), name="orders"),
    path("notifications/", views.DashboardNotificationsView.as_view(), name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        views.NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    path("wishlist/", views.DashboardWishlistView.as_view(), name="wishlist"),
    path(
        "wishlist/courses/<int:pk>/toggle/",
        views.CourseWishlistToggleView.as_view(),
        name="wishlist-toggle-course",
    ),
    path(
        "wishlist/products/<int:pk>/toggle/",
        views.ProductWishlistToggleView.as_view(),
        name="wishlist-toggle-product",
    ),
]
