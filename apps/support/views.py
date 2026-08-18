from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, TemplateView

from apps.core.tasks import safe_delay

from .forms import TicketForm
from .models import FAQItem, HelpCategory, SupportTicket
from .services import search_faqs
from .tasks import notify_team_new_ticket_task


class SupportHomeView(TemplateView):
    template_name = "support/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(
            {
                "categories": HelpCategory.objects.annotate(
                    articles_count=Count(
                        "kb_articles", filter=Q(kb_articles__is_published=True), distinct=True
                    )
                ),
                "faqs": FAQItem.objects.select_related("category"),
                "SUPPORT_TEAM_EMAIL": settings.SUPPORT_TEAM_EMAIL,
                "whatsapp_url": (
                    f"https://wa.me/{settings.SUPPORT_WHATSAPP_NUMBER}"
                    if settings.SUPPORT_WHATSAPP_NUMBER
                    else ""
                ),
                "ticket_form": TicketForm(
                    initial={
                        "full_name": user.get_full_name() if user.is_authenticated else "",
                        "email": user.email if user.is_authenticated else "",
                    }
                ),
            }
        )
        return context


class CategoryDetailView(DetailView):
    model = HelpCategory
    template_name = "support/category.html"
    context_object_name = "category"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["articles"] = self.object.kb_articles.filter(is_published=True)
        return context


class FaqSearchView(View):
    def get(self, request):
        query = request.GET.get("q", "")
        results = search_faqs(query)
        return JsonResponse(
            {
                "results": [
                    {
                        "id": faq.pk,
                        "question": faq.question,
                        "category": faq.category.name if faq.category else "",
                    }
                    for faq in results
                ]
            }
        )


class TicketCreateView(View):
    def post(self, request):
        form = TicketForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, _("برجاء مراجعة بيانات التذكرة والمحاولة مرة أخرى."))
            return redirect("support:home")

        ticket = SupportTicket.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=form.cleaned_data["full_name"],
            email=form.cleaned_data["email"],
            category=form.cleaned_data["category"],
            subject=form.cleaned_data["subject"],
            body=form.cleaned_data["body"],
            attachment=form.cleaned_data["attachment"],
        )
        safe_delay(notify_team_new_ticket_task, ticket.pk)
        messages.success(request, _("تم إرسال تذكرتك بنجاح، بنرد خلال 24 ساعة في أيام العمل."))
        return redirect("support:home")
