from django.db import models

from apps.core.validators import validate_image_extension, validate_image_size


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Subclasses with an ImageField list its name(s) here to get automatic
    # resize/re-encode-on-upload for free (apps.core.images.
    # compress_image_field) — keeps page weight down without every model
    # having to repeat the same save() plumbing.
    image_fields_to_compress = []

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.image_fields_to_compress:
            from apps.core.images import compress_image_field

            for field_name in self.image_fields_to_compress:
                compress_image_field(getattr(self, field_name))
        super().save(*args, **kwargs)


class SiteSetting(TimeStampedModel):
    VALUE_TYPE_CHOICES = [
        ("string", "string"),
        ("int", "int"),
        ("bool", "bool"),
        ("json", "json"),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default="string")

    def __str__(self):
        return self.key


class HomepageContent(TimeStampedModel):
    """Editable copy for the homepage hero — a single row (seeded by a data
    migration), edited from the staff panel instead of hardcoded in
    templates/core/home.html. Falls back to that template's original
    hardcoded copy/image when a field is left blank, so an empty row still
    renders a sensible homepage."""

    hero_title = models.CharField(max_length=255, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_image = models.ImageField(
        upload_to="homepage/",
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_image_size],
    )

    image_fields_to_compress = ["hero_image"]

    def __str__(self):
        return "Homepage content"
