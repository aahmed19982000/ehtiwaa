from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.courses.models import Course
from apps.specialists.models import Specialist
from apps.store.models import Product

from .forms import ReviewForm
from .services import submit_review


class BaseReviewCreateView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    model = None

    def get_redirect_url(self, obj):
        raise NotImplementedError

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        form = ReviewForm(request.POST)
        if form.is_valid():
            submit_review(
                request.user, obj, int(form.cleaned_data["rating"]), form.cleaned_data["comment"]
            )
            messages.success(request, _("شكراً لتقييمك!"))
        else:
            messages.error(request, _("برجاء اختيار تقييم صحيح."))
        return redirect(self.get_redirect_url(obj))


class SpecialistReviewCreateView(BaseReviewCreateView):
    model = Specialist

    def get_redirect_url(self, obj):
        return reverse("specialists:detail", args=[obj.pk])


class CourseReviewCreateView(BaseReviewCreateView):
    model = Course

    def get_redirect_url(self, obj):
        return reverse("courses:detail", args=[obj.slug])


class ProductReviewCreateView(BaseReviewCreateView):
    model = Product

    def get_redirect_url(self, obj):
        return reverse("store:detail", args=[obj.slug])
