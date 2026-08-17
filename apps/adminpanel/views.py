from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView

from apps.specialists.models import Specialist

from .forms import ReviewDecisionForm
from .services import approve_specialist, reject_specialist


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Independent ops panel, separate from Django Admin — gated to any
    staff account. Finance Manager staff have no Specialist permission at
    all (see the Finance Manager group's scoped permissions), so this is
    effectively Super Admin / specialist-approver territory in practice."""

    login_url = "accounts:login"

    def test_func(self):
        return self.request.user.is_staff


class PendingSpecialistListView(StaffRequiredMixin, ListView):
    model = Specialist
    template_name = "adminpanel/pending_specialists.html"
    context_object_name = "specialists"

    def get_queryset(self):
        return (
            Specialist.objects.filter(status="pending")
            .select_related("user")
            .prefetch_related("credential_documents")
            .order_by("created_at")
        )


class SpecialistApproveView(StaffRequiredMixin, View):
    def post(self, request, pk):
        specialist = get_object_or_404(Specialist, pk=pk, status="pending")
        form = ReviewDecisionForm(request.POST)
        notes = form.cleaned_data["notes"] if form.is_valid() else ""
        approve_specialist(specialist, request.user, notes)
        messages.success(request, _("تم اعتماد الأخصائي."))
        return redirect("adminpanel:pending-specialists")


class SpecialistRejectView(StaffRequiredMixin, View):
    def post(self, request, pk):
        specialist = get_object_or_404(Specialist, pk=pk, status="pending")
        form = ReviewDecisionForm(request.POST)
        notes = form.cleaned_data["notes"] if form.is_valid() else ""
        reject_specialist(specialist, request.user, notes)
        messages.success(request, _("تم رفض الطلب."))
        return redirect("adminpanel:pending-specialists")
