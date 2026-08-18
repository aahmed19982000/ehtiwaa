from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_image_extension, validate_image_size


class User(AbstractUser):
    ROLE_CHOICES = [
        ("client", "client"),
        ("specialist", "specialist"),
        ("admin", "admin"),
    ]

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="client")
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class Profile(TimeStampedModel):
    GENDER_CHOICES = [("male", "male"), ("female", "female")]

    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_image_size],
    )
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    city = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"
