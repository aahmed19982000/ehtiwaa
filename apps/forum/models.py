from django.db import models

from apps.core.models import TimeStampedModel


class Tag(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Question(TimeStampedModel):
    author = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="forum_questions"
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    tags = models.ManyToManyField("forum.Tag", related_name="questions", blank=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Answer(TimeStampedModel):
    question = models.ForeignKey("forum.Question", on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="forum_answers"
    )
    body = models.TextField()
    is_accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer<{self.question_id}>"


class Vote(TimeStampedModel):
    VALUE_CHOICES = [(1, "up"), (-1, "down")]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="forum_votes")
    answer = models.ForeignKey("forum.Answer", on_delete=models.CASCADE, related_name="votes")
    value = models.SmallIntegerField(choices=VALUE_CHOICES)

    class Meta:
        unique_together = [("user", "answer")]

    def __str__(self):
        return f"Vote<{self.user_id}:{self.answer_id}>"
