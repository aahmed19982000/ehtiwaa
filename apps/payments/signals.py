from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Payment
from .services import handle_payment_succeeded


@receiver(post_save, sender=Payment)
def on_payment_saved(sender, instance, **kwargs):
    """Single source of truth for "a Payment just succeeded" — covers both
    a Paymob webhook marking it succeeded and an admin manually confirming
    a bank transfer. handle_payment_succeeded is itself idempotent, so a
    re-save (webhook retry, admin re-opening and saving the same Payment)
    is a harmless no-op rather than a duplicate enrollment/confirmation."""
    if instance.status == "succeeded":
        handle_payment_succeeded(instance)
