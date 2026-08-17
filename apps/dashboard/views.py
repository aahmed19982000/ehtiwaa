from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from apps.bookings.models import Booking
from apps.courses.models import Course, Enrollment
from apps.notifications.models import Notification
from apps.payments.models import Order
from apps.store.models import Product

from .models import WishlistItem


class DashboardTabMixin(LoginRequiredMixin):
    login_url = "accounts:login"
    active_tab = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = self.active_tab
        return context


class DashboardBookingsView(DashboardTabMixin, TemplateView):
    template_name = "dashboard/bookings.html"
    active_tab = "bookings"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bookings"] = Booking.objects.filter(client=self.request.user).select_related(
            "specialist"
        )
        return context


class DashboardCoursesView(DashboardTabMixin, TemplateView):
    template_name = "dashboard/courses.html"
    active_tab = "courses"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enrollments"] = Enrollment.objects.filter(user=self.request.user).select_related(
            "course"
        )
        return context


class DashboardOrdersView(DashboardTabMixin, TemplateView):
    template_name = "dashboard/orders.html"
    active_tab = "orders"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders"] = (
            Order.objects.filter(user=self.request.user)
            .select_related("invoice")
            .prefetch_related("items")
            .order_by("-created_at")
        )
        return context


class DashboardNotificationsView(DashboardTabMixin, TemplateView):
    template_name = "dashboard/notifications.html"
    active_tab = "notifications"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notifications"] = Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )
        return context


class NotificationMarkReadView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return redirect("dashboard:notifications")


class DashboardWishlistView(DashboardTabMixin, TemplateView):
    template_name = "dashboard/wishlist.html"
    active_tab = "wishlist"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wishlist_items"] = WishlistItem.objects.filter(
            user=self.request.user
        ).select_related("content_type")
        return context


class WishlistToggleView(LoginRequiredMixin, View):
    """Shared toggle behavior for the two wishlist-able models — subclasses
    just set `model` and where to bounce back to."""

    login_url = "accounts:login"
    model = None

    def get_redirect_url(self, obj):
        raise NotImplementedError

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        content_type = ContentType.objects.get_for_model(self.model)
        item, created = WishlistItem.objects.get_or_create(
            user=request.user, content_type=content_type, object_id=obj.pk
        )
        if not created:
            item.delete()
            messages.success(request, _("تمت الإزالة من المفضلة."))
        else:
            messages.success(request, _("تمت الإضافة للمفضلة."))
        return redirect(self.get_redirect_url(obj))


class CourseWishlistToggleView(WishlistToggleView):
    model = Course

    def get_redirect_url(self, obj):
        return reverse("courses:detail", args=[obj.slug])


class ProductWishlistToggleView(WishlistToggleView):
    model = Product

    def get_redirect_url(self, obj):
        return reverse("store:detail", args=[obj.slug])
