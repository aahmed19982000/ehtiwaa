from django.contrib import admin

from .models import Certificate, Course, Enrollment, Lesson, Module

admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(Certificate)
