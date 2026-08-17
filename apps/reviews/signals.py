from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review


def _recompute(content_type, object_id):
    """Rewrites average_rating/reviews_count on whatever content_object this
    review targets — a no-op for any model that doesn't carry those fields,
    so Review stays usable against entities that don't display ratings."""
    model_class = content_type.model_class()
    if model_class is None or not hasattr(model_class, "average_rating"):
        return
    stats = Review.objects.filter(content_type=content_type, object_id=object_id).aggregate(
        avg=Avg("rating"), count=Count("id")
    )
    model_class.objects.filter(pk=object_id).update(
        average_rating=stats["avg"] or 0, reviews_count=stats["count"]
    )


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    _recompute(instance.content_type, instance.object_id)


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    _recompute(instance.content_type, instance.object_id)
