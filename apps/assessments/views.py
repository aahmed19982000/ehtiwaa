from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView

from .models import Assessment, Attempt
from .services import owns_attempt, record_answer, score_attempt, start_attempt


class AssessmentListView(ListView):
    model = Assessment
    template_name = "assessments/list.html"
    context_object_name = "assessments"

    def get_queryset(self):
        return Assessment.objects.filter(is_published=True).order_by("title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = (
            Assessment.objects.filter(is_published=True)
            .exclude(category="")
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )
        return context


class AssessmentStartView(View):
    def post(self, request, slug):
        assessment = get_object_or_404(Assessment, slug=slug, is_published=True)
        attempt = start_attempt(request, assessment)
        return redirect("assessments:take", token=attempt.share_token, question_number=1)


class AssessmentTakeView(View):
    template_name = "assessments/take.html"

    def _load(self, request, token, question_number):
        attempt = get_object_or_404(Attempt.objects.select_related("assessment"), share_token=token)
        if not owns_attempt(request, attempt) or attempt.completed_at:
            raise Http404
        questions = list(attempt.assessment.questions.prefetch_related("options"))
        if not questions or not (1 <= question_number <= len(questions)):
            raise Http404
        return attempt, questions

    def get(self, request, token, question_number):
        attempt, questions = self._load(request, token, question_number)
        question = questions[question_number - 1]
        selected_option_id = (
            attempt.selected_options.filter(question=question).values_list("id", flat=True).first()
        )
        return render(
            request,
            self.template_name,
            {
                "attempt": attempt,
                "assessment": attempt.assessment,
                "question": question,
                "question_number": question_number,
                "total_questions": len(questions),
                "progress_percent": round(question_number / len(questions) * 100),
                "selected_option_id": selected_option_id,
            },
        )

    def post(self, request, token, question_number):
        attempt, questions = self._load(request, token, question_number)
        question = questions[question_number - 1]

        option = question.options.filter(pk=request.POST.get("option")).first()
        if not option:
            messages.error(request, _("برجاء اختيار إجابة قبل المتابعة."))
            return redirect("assessments:take", token=token, question_number=question_number)

        record_answer(attempt, question, option)

        if question_number < len(questions):
            return redirect("assessments:take", token=token, question_number=question_number + 1)

        score_attempt(attempt)
        return redirect("assessments:result", token=token)


class AssessmentResultView(View):
    """Keyed by the same opaque share_token as the take flow — deliberately
    open to anyone with the link (not owner-restricted), since "شارك
    النتيجة" means the result page itself IS the share link."""

    template_name = "assessments/result.html"

    def get(self, request, token):
        attempt = get_object_or_404(
            Attempt.objects.select_related("assessment", "result_level"),
            share_token=token,
            completed_at__isnull=False,
        )
        return render(
            request, self.template_name, {"attempt": attempt, "assessment": attempt.assessment}
        )
