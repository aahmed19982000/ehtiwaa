from django.contrib import admin

from .models import Article, Banner, Testimonial, Video

admin.site.register(Article)
admin.site.register(Video)
admin.site.register(Testimonial)
admin.site.register(Banner)
