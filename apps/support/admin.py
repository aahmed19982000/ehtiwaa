from django.contrib import admin

from .models import FAQItem, HelpCategory, KBArticle, SupportTicket

admin.site.register(HelpCategory)
admin.site.register(FAQItem)
admin.site.register(KBArticle)
admin.site.register(SupportTicket)
