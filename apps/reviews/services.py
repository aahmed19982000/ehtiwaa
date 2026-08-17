from django.contrib.contenttypes.models import ContentType

from .models import Review


def submit_review(user, obj, rating, comment=""):
    """One review per user per object — resubmitting updates it in place
    rather than creating a second row, so users can revise their rating."""
    review, _created = Review.objects.update_or_create(
        user=user,
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        defaults={"rating": rating, "comment": comment},
    )
    return review
