from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.accounts import auth0
from apps.bookings.services import get_next_available_slots
from apps.reviews.models import Review

from .forms import SpecialistApplicationForm, SpecialistDirectoryFilterForm, SpecialistDocumentsForm
from .models import CredentialDocument, Specialist


class SpecialistLandingView(TemplateView):
    """Public marketing page introducing the specialist program — the
    actual application (SpecialistApplyView) is linked from here."""

    template_name = "specialists/landing.html"


class SpecialistDirectoryView(ListView):
    """Public directory (دليل الأخصائيين) — search, filter, sort and
    paginate over approved specialists only (unapproved profiles never
    appear here or on the detail page, per the report's RBAC section)."""

    model = Specialist
    template_name = "specialists/directory.html"
    context_object_name = "specialists"
    paginate_by = 12

    def get_queryset(self):
        self.filter_form = SpecialistDirectoryFilterForm(self.request.GET or None)
        qs = (
            Specialist.objects.filter(status="approved")
            .select_related("user__profile")
            .prefetch_related("specialties")
        )

        if not self.filter_form.is_valid():
            return qs.order_by("-average_rating")

        data = self.filter_form.cleaned_data

        q = data.get("q")
        if q:
            qs = qs.filter(
                Q(full_name_ar__icontains=q)
                | Q(full_name_en__icontains=q)
                | Q(headline__icontains=q)
                | Q(about__icontains=q)
                | Q(specialties__name__icontains=q)
            ).distinct()

        if data.get("category"):
            qs = qs.filter(category=data["category"])
        if data.get("gender"):
            qs = qs.filter(gender=data["gender"])
        if data.get("language"):
            qs = qs.filter(languages__contains=[data["language"]])
        if data.get("duration") == "60":
            qs = qs.filter(hourly_rate__isnull=False)
        elif data.get("duration") == "30":
            qs = qs.filter(price_30min__isnull=False)
        if data.get("min_rating"):
            qs = qs.filter(average_rating__gte=int(data["min_rating"]))
        if data.get("can_prescribe"):
            qs = qs.filter(category="psychiatrist")
        if data.get("price_min") is not None:
            qs = qs.filter(hourly_rate__gte=data["price_min"])
        if data.get("price_max") is not None:
            qs = qs.filter(hourly_rate__lte=data["price_max"])
        if data.get("available_only"):
            qs = qs.filter(next_available_date__isnull=False)

        sort = data.get("sort")
        if sort == "price_asc":
            qs = qs.order_by(F("hourly_rate").asc(nulls_last=True))
        elif sort == "availability":
            qs = qs.order_by(F("next_available_date").asc(nulls_last=True))
        else:
            qs = qs.order_by("-average_rating")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["has_active_filters"] = self.filter_form.has_active_filters()
        # Real availability data, not the static admin-editable
        # next_available_date field — computed only for this page's 12
        # specialists (not the whole filtered queryset), same reasoning as
        # any other per-page-only enrichment.
        page_specialists = context["specialists"]
        next_slots = get_next_available_slots(page_specialists)
        for specialist in page_specialists:
            specialist.next_available_slot = next_slots.get(specialist.pk)
        return context


class SpecialistDetailView(DetailView):
    model = Specialist
    template_name = "specialists/detail.html"
    context_object_name = "specialist"
    queryset = (
        Specialist.objects.filter(status="approved")
        .select_related("user__profile")
        .prefetch_related("specialties")
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_type = ContentType.objects.get_for_model(Specialist)
        context["reviews"] = (
            Review.objects.filter(content_type=content_type, object_id=self.object.pk)
            .select_related("user")
            .order_by("-created_at")[:20]
        )
        return context


class SpecialistApplyView(FormView):
    """No login required — matches Shezlong's own professional/registration
    page, which collects account details (email/password) together with the
    application in one form rather than gating behind a separate signup
    step. Anonymous submissions create the Auth0 account first (same
    apps.accounts.auth0 pipeline as accounts.views.SignupView), then the
    specialist application, in one go."""

    template_name = "specialists/apply.html"
    form_class = SpecialistApplicationForm
    # Documents come after the account/application exists (step 2) —
    # requested explicitly so file uploads aren't asked for before there's
    # even an account to attach them to.
    success_url = reverse_lazy("specialists:apply-documents")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            specialist = getattr(request.user, "specialist_profile", None)
            if specialist:
                if CredentialDocument.objects.filter(specialist=specialist).exists():
                    return redirect("specialists:apply-pending")
                return redirect("specialists:apply-documents")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        data = form.cleaned_data
        user = self.request.user

        if not user.is_authenticated:
            full_name = data["full_name_ar"] or data["full_name_en"]
            signup_failed_login_error = _("تم إنشاء حسابك، لكن تعذّر تسجيل دخولك تلقائيًا.")
            try:
                auth0.signup(email=data["email"], password=data["password1"], name=full_name)
                token_data = auth0.login(
                    email=data["email"],
                    password=data["password1"],
                    generic_error=signup_failed_login_error,
                )
                userinfo = auth0.get_userinfo(
                    token_data["access_token"], generic_error=signup_failed_login_error
                )
            except auth0.Auth0Error as exc:
                form.add_error(None, str(exc))
                return self.form_invalid(form)

            provider = get_adapter().get_provider(self.request, "auth0")
            sociallogin = provider.sociallogin_from_response(self.request, userinfo)
            name_parts = data["full_name_en"].strip().split(" ", 1)
            sociallogin.user.first_name = name_parts[0]
            sociallogin.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
            if data.get("full_phone"):
                sociallogin.user.phone = data["full_phone"]

            complete_social_login(self.request, sociallogin)
            user = self.request.user
            if not user.is_authenticated:
                # The adapter's pre_social_login bailed out (e.g. email tied
                # to an existing unverified account) and already flashed a
                # message explaining why — just stop here.
                form.add_error(None, _("تعذّر إنشاء الحساب. برجاء المحاولة مرة أخرى."))
                return self.form_invalid(form)

        Specialist.objects.create(
            user=user,
            status="pending",
            category=data["category"],
            full_name_ar=data["full_name_ar"],
            full_name_en=data["full_name_en"],
            title=data["title"],
            birth_year=data["birth_year"],
            gender=data["gender"],
            nationality=data["nationality"],
            country_of_residence=data["country_of_residence"],
            languages=data["languages"],
            years_of_experience=data.get("years_of_experience") or 0,
        )

        update_fields = []
        if data.get("full_phone") and user.phone != data["full_phone"]:
            user.phone = data["full_phone"]
            update_fields.append("phone")
        if user.role != "specialist":
            user.role = "specialist"
            update_fields.append("role")
        if update_fields:
            user.save(update_fields=update_fields)

        return super().form_valid(form)


class SpecialistDocumentsView(LoginRequiredMixin, FormView):
    """Step 2 — credential document uploads. Requires the login step 1
    already established, and a Specialist record (application) to attach
    the documents to."""

    template_name = "specialists/apply_documents.html"
    form_class = SpecialistDocumentsForm
    login_url = reverse_lazy("accounts:login")
    success_url = reverse_lazy("specialists:apply-pending")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.specialist = getattr(request.user, "specialist_profile", None)

    def _blocked_response(self):
        """None if the request may proceed; otherwise where to send it
        instead. Only meaningful once LoginRequiredMixin has already let an
        authenticated request through to get()/post()."""
        if not self.specialist:
            return redirect("specialists:apply")
        if CredentialDocument.objects.filter(specialist=self.specialist).exists():
            return redirect("specialists:apply-pending")
        return None

    def get(self, request, *args, **kwargs):
        return self._blocked_response() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._blocked_response() or super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["category"] = self.specialist.category
        return kwargs

    def form_valid(self, form):
        for _field_name, label, uploaded_file in form.documents():
            CredentialDocument.objects.create(
                specialist=self.specialist, label=label, file=uploaded_file
            )
        return super().form_valid(form)


class SpecialistApplyPendingView(LoginRequiredMixin, TemplateView):
    template_name = "specialists/apply_pending.html"
    login_url = reverse_lazy("accounts:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["specialist"] = getattr(self.request.user, "specialist_profile", None)
        return context
