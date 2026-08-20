from django.db.models import Avg, Q
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.content.models import Article, Banner, Testimonial, Video
from apps.core.models import HomepageContent
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

    def _featured_then_fallback(self, base_queryset, fallback_order_by, limit):
        """Staff-picked (`is_featured`) rows first, most-recently-picked
        first; topped up with `base_queryset` ordered by `fallback_order_by`
        (excluding whatever's already picked) so the section is never
        short before any staff picks exist."""
        featured = list(base_queryset.filter(is_featured=True).order_by("-updated_at")[:limit])
        if len(featured) < limit:
            featured_ids = [obj.pk for obj in featured]
            remaining = limit - len(featured)
            fallback = list(
                base_queryset.exclude(pk__in=featured_ids).order_by(fallback_order_by)[:remaining]
            )
            featured.extend(fallback)
        return featured

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed_sessions = Booking.objects.filter(status="completed").count()
        completed_courses = Enrollment.objects.filter(completed_at__isnull=False).count()

        specialists_base = Specialist.objects.filter(status="approved").select_related("user__profile")
        courses_base = Course.objects.filter(is_published=True)
        videos_base = Video.objects.filter(is_published=True)

        context.update(
            {
                "homepage_content": HomepageContent.objects.first() or HomepageContent(),
                "hero_banner": self._active_banners("home_hero").first(),
                "small_banners": self._active_banners("home_small_grid")[:3],
                "specialty_tags": SpecialtyTag.objects.all()[:8],
                "specialists": self._featured_then_fallback(specialists_base, "-average_rating", 4),
                "courses": self._featured_then_fallback(courses_base, "-average_rating", 4),
                "articles": Article.objects.filter(is_published=True)
                .select_related("author")
                .order_by("-published_at")[:4],
                "videos": self._featured_then_fallback(videos_base, "-created_at", 4),
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
