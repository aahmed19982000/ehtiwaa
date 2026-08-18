from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Answer, Question

User = get_user_model()


class AcceptAnswerPermissionTests(TestCase):
    """IDOR check: accepting an answer changes state on someone else's
    Question (who gets the "أفضل إجابة" badge) — only the question's own
    author may do it (apps.forum.services.accept_answer)."""

    def setUp(self):
        self.question_author = User.objects.create_user(
            username="asker", email="asker@example.com", password="whatever-123"
        )
        self.other_user = User.objects.create_user(
            username="rando", email="rando@example.com", password="whatever-123"
        )
        self.answerer = User.objects.create_user(
            username="answerer", email="answerer@example.com", password="whatever-123"
        )
        self.question = Question.objects.create(
            author=self.question_author, title="سؤال تجريبي", body="نص السؤال"
        )
        self.answer = Answer.objects.create(
            question=self.question, author=self.answerer, body="إجابة تجريبية"
        )
        self.accept_url = reverse("forum:accept-answer", kwargs={"pk": self.answer.pk})

    def test_question_author_can_accept_answer(self):
        self.client.force_login(self.question_author)
        self.client.post(self.accept_url)
        self.answer.refresh_from_db()
        self.assertTrue(self.answer.is_accepted)

    def test_other_user_cannot_accept_answer(self):
        self.client.force_login(self.other_user)
        self.client.post(self.accept_url)
        self.answer.refresh_from_db()
        self.assertFalse(self.answer.is_accepted)

    def test_answers_own_author_cannot_accept_their_own_answer(self):
        # Only the *question* author decides — not even whoever wrote the answer.
        self.client.force_login(self.answerer)
        self.client.post(self.accept_url)
        self.answer.refresh_from_db()
        self.assertFalse(self.answer.is_accepted)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.post(self.accept_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.answer.refresh_from_db()
        self.assertFalse(self.answer.is_accepted)


class ContentEscapingTests(TestCase):
    """A <script> tag typed into a question/answer body must render as
    inert text on the page, not execute — Django's autoescaping should
    already guarantee this as long as no template opts out with |safe."""

    XSS_PAYLOAD = "<script>alert('xss')</script>"

    def setUp(self):
        self.user = User.objects.create_user(
            username="xssuser", email="xssuser@example.com", password="whatever-123"
        )

    def test_question_body_is_escaped_on_detail_page(self):
        question = Question.objects.create(
            author=self.user, title="عنوان عادي", body=self.XSS_PAYLOAD
        )
        response = self.client.get(reverse("forum:detail", kwargs={"pk": question.pk}))
        self.assertNotContains(response, self.XSS_PAYLOAD, html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)

    def test_answer_body_is_escaped_on_detail_page(self):
        question = Question.objects.create(author=self.user, title="سؤال", body="نص")
        Answer.objects.create(question=question, author=self.user, body=self.XSS_PAYLOAD)
        response = self.client.get(reverse("forum:detail", kwargs={"pk": question.pk}))
        self.assertNotContains(response, self.XSS_PAYLOAD, html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)

    def test_question_title_is_escaped_on_list_page(self):
        Question.objects.create(author=self.user, title=self.XSS_PAYLOAD, body="نص")
        response = self.client.get(reverse("forum:list"))
        self.assertNotContains(response, self.XSS_PAYLOAD, html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)
