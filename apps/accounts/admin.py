from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Profile, User


class EhtiwaaUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "username", "role", "is_staff", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("Ehtiwaa", {"fields": ("phone", "role", "is_phone_verified", "is_email_verified")}),
    )


admin.site.register(User, EhtiwaaUserAdmin)
admin.site.register(Profile)
