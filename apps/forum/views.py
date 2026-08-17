from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView

from .forms import AnswerForm, AskQuestionForm, ReportForm
from .models import Answer, Question, Tag, Vote
from .services import accept_answer, create_report, toggle_helpful_vote


class QuestionListView(ListView):
    model = Question
    template_name = "forum/list.html"
    context_object_name = "questions"
    paginate_by = 15

    def get_queryset(self):
        qs = (
            Question.objects.select_related("author")
            .prefetch_related("tags")
            .annotate(answers_count=Count("answers", distinct=True))
            .order_by("-created_at")
        )
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(body__icontains=query))
        tag_slug = self.request.GET.get("tag")
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tags"] = Tag.objects.order_by("name")
        context["active_tag"] = self.request.GET.get("tag", "")
        context["query"] = self.request.GET.get("q", "")
        return context


class AskQuestionView(LoginRequiredMixin, View):
    template_name = "forum/ask.html"
    login_url = "accounts:login"

    def get(self, request):
        return render(request, self.template_name, {"form": AskQuestionForm()})

    def post(self, request):
        form = AskQuestionForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        question = Question.objects.create(
            author=request.user,
            title=form.cleaned_data["title"],
            body=form.cleaned_data["body"],
        )
        for name in form.cleaned_data["tags"]:
            tag, _created = Tag.objects.get_or_create(
                slug=slugify(name, allow_unicode=True), defaults={"name": name}
            )
            question.tags.add(tag)

        messages.success(request, _("تم نشر سؤالك بنجاح."))
        return redirect("forum:detail", pk=question.pk)


class QuestionDetailView(DetailView):
    model = Question
    template_name = "forum/detail.html"
    context_object_name = "question"

    def get_queryset(self):
        return Question.objects.select_related("author").prefetch_related("tags")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        Question.objects.filter(pk=self.object.pk).update(views_count=F("views_count") + 1)
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.object

        answers = list(
            question.answers.select_related("author__specialist_profile").prefetch_related("votes")
        )
        voted_ids = set()
        if self.request.user.is_authenticated:
            voted_ids = set(
                Vote.objects.filter(user=self.request.user, answer__question=question).values_list(
                    "answer_id", flat=True
                )
            )
        for answer in answers:
            answer.helpful_count = len(answer.votes.all())
            answer.user_found_helpful = answer.pk in voted_ids

        related_questions = (
            Question.objects.filter(tags__in=question.tags.all())
            .exclude(pk=question.pk)
            .distinct()[:3]
        )

        context.update(
            {
                "answers": answers,
                "answer_form": AnswerForm(),
                "related_questions": related_questions,
            }
        )
        return context


class PostAnswerView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        form = AnswerForm(request.POST)
        if form.is_valid():
            Answer.objects.create(
                question=question, author=request.user, body=form.cleaned_data["body"]
            )
            messages.success(request, _("تم نشر إجابتك."))
        else:
            messages.error(request, _("برجاء كتابة نص الإجابة."))
        return redirect("forum:detail", pk=pk)


class AcceptAnswerView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, pk):
        answer = get_object_or_404(Answer.objects.select_related("question"), pk=pk)
        try:
            accept_answer(answer.question, answer, request.user)
            messages.success(request, _("تم اعتماد الإجابة كأفضل إجابة."))
        except PermissionError:
            messages.error(request, _("لا يمكنك اعتماد إجابة على سؤال غيرك."))
        return redirect("forum:detail", pk=answer.question_id)


class ToggleHelpfulView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        toggle_helpful_vote(request.user, answer)
        return redirect("forum:detail", pk=answer.question_id)


class ReportQuestionView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        form = ReportForm(request.POST)
        create_report(
            request.user, question, form.cleaned_data["reason"] if form.is_valid() else ""
        )
        messages.success(request, _("تم استلام بلاغك، شكراً لمساعدتك في الحفاظ على المجتمع."))
        return redirect("forum:detail", pk=pk)


class ReportAnswerView(LoginRequiredMixin, View):
    login_url = "accounts:login"

    def post(self, request, pk):
        answer = get_object_or_404(Answer, pk=pk)
        form = ReportForm(request.POST)
        create_report(request.user, answer, form.cleaned_data["reason"] if form.is_valid() else "")
        messages.success(request, _("تم استلام بلاغك، شكراً لمساعدتك في الحفاظ على المجتمع."))
        return redirect("forum:detail", pk=answer.question_id)
