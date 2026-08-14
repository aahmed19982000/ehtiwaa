from django.contrib import admin

from .models import ApprovalRequest, CredentialDocument, Specialist, SpecialtyTag

admin.site.register(SpecialtyTag)
admin.site.register(Specialist)
admin.site.register(ApprovalRequest)
admin.site.register(CredentialDocument)
