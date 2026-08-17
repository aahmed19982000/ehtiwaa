from django.db.models import Avg, Q
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.content.models import Article, Banner, Testimonial, Video
from apps.courses.models import Course, Enrollment
from apps.reviews.models import Review
from apps.specialists.models import Specialist, SpecialtyTag


class TermsView(TemplateView):
    template_name = "core/terms.html"


class PrivacyView(TemplateView):
    template_name = "core/privacy.html"


class HomeView(TemplateView):
    template_name = "core/home.html"

    def _active_banners(self, placement):
        now = timezone.now()
        return Banner.objects.filter(placement=placement, is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed_sessions = Booking.objects.filter(status="completed").count()
        completed_courses = Enrollment.objects.filter(completed_at__isnull=False).count()
        context.update(
            {
                "hero_banner": self._active_banners("home_hero").first(),
                "small_banners": self._active_banners("home_small_grid")[:3],
                "specialty_tags": SpecialtyTag.objects.all()[:8],
                "specialists": Specialist.objects.filter(status="approved")
                .select_related("user__profile")
                .order_by("-average_rating")[:4],
                "courses": Course.objects.filter(is_published=True).order_by("-average_rating")[:4],
                "articles": Article.objects.filter(is_published=True)
                .select_related("author")
                .order_by("-published_at")[:4],
                "videos": Video.objects.filter(is_published=True).order_by("-created_at")[:4],
                "testimonials": Testimonial.objects.filter(is_active=True)[:3],
                "stats": {
                    "specialists_count": Specialist.objects.filter(status="approved").count(),
                    "users_count": User.objects.count(),
                    "completed_count": completed_sessions + completed_courses,
                    "avg_rating": Review.objects.aggregate(avg=Avg("rating"))["avg"] or 0,
                },
            }
        )
        return context
