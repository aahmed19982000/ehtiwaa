from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from .models import MatchResult, QuizQuestion
from .services import generate_match_result, new_run_token, owns_run, record_response


class MatchFinderIntroView(TemplateView):
    template_name = "matchfinder/intro.html"


class MatchFinderStartView(View):
    def post(self, request):
        if not QuizQuestion.objects.exists():
            raise Http404
        run_token = new_run_token()
        return redirect("matchfinder:question", run_token=run_token, question_number=1)


class MatchFinderQuestionView(View):
    template_name = "matchfinder/question.html"

    def _load(self, request, run_token, question_number):
        if not owns_run(request, run_token):
            raise Http404
        questions = list(QuizQuestion.objects.prefetch_related("choices"))
        if not questions or not (1 <= question_number <= len(questions)):
            raise Http404
        return questions

    def get(self, request, run_token, question_number):
        questions = self._load(request, run_token, question_number)
        question = questions[question_number - 1]
        return render(
            request,
            self.template_name,
            {
                "run_token": run_token,
                "question": question,
                "question_number": question_number,
                "total_questions": len(questions),
                "progress_percent": round(question_number / len(questions) * 100),
            },
        )

    def post(self, request, run_token, question_number):
        questions = self._load(request, run_token, question_number)
        question = questions[question_number - 1]

        choice = question.choices.filter(pk=request.POST.get("choice")).first()
        if not choice:
            return redirect(
                "matchfinder:question", run_token=run_token, question_number=question_number
            )

        record_response(request, run_token, question, choice)

        if question_number < len(questions):
            return redirect(
                "matchfinder:question", run_token=run_token, question_number=question_number + 1
            )

        result = MatchResult.objects.filter(run_token=run_token).first()
        if not result:
            result = generate_match_result(request, run_token)
        return redirect("matchfinder:results", run_token=result.run_token)


class MatchFinderResultsView(View):
    """Keyed by run_token — open to anyone with the link, same reasoning as
    assessments' share_token result pages."""

    template_name = "matchfinder/results.html"

    def get(self, request, run_token):
        result = get_object_or_404(
            MatchResult.objects.prefetch_related("items__specialist__user__profile"),
            run_token=run_token,
        )
        return render(
            request, self.template_name, {"result": result, "matches": result.items.all()}
        )
