from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimeStampedModel


class WishlistItem(TimeStampedModel):
    """Generic bookmark — a courses.Course or store.Product a user wants to
    come back to. Same GenericForeignKey pattern as apps.reviews.Review."""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="wishlist_items"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = [("user", "content_type", "object_id")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"WishlistItem<{self.user_id}:{self.content_type_id}:{self.object_id}>"
