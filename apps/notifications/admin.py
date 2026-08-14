from django.contrib import admin

from .models import MessageLog, Notification

admin.site.register(Notification)
admin.site.register(MessageLog)
