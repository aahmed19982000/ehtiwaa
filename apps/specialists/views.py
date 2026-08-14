from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.accounts import services as account_services

from .forms import SpecialistApplicationForm
from .models import CredentialDocument, Specialist


class SpecialistApplyView(FormView):
    template_name = "specialists/apply.html"
    form_class = SpecialistApplicationForm
    success_url = reverse_lazy("accounts:signup-check-email")

    def form_valid(self, form):
        data = form.cleaned_data
        full_name = data["full_name_ar"] or data["full_name_en"]

        user = account_services.create_local_user(
            email=data["email"],
            phone=data.get("full_phone"),
            full_name=full_name,
            password=data["password1"],
            role="specialist",
            username=data["username"],
        )

        specialist = Specialist.objects.create(
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

        for _field_name, label, uploaded_file in form.documents_for_category():
            CredentialDocument.objects.create(
                specialist=specialist, label=label, file=uploaded_file
            )

        account_services.send_activation_email(user, request=self.request)
        self.request.session["signup_email"] = user.email
        return super().form_valid(form)
