from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimeStampedModel

RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]


class Review(TimeStampedModel):
    """Generic rating/review attachable to any entity — a
    specialists.Specialist, courses.Course, or store.Product — via
    Django's contenttypes framework."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reviews")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"Review<{self.user_id}:{self.rating}>"
