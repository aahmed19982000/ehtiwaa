from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
