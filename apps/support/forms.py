from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_document_extension, validate_document_size

from .models import HelpCategory


class TicketForm(forms.Form):
    full_name = forms.CharField(label=_("الاسم الكامل"), max_length=150)
    email = forms.EmailField(label=_("البريد الإلكتروني"))
    category = forms.ModelChoiceField(
        label=_("التصنيف"),
        queryset=HelpCategory.objects.all(),
        required=False,
        empty_label=_("اختر التصنيف"),
    )
    subject = forms.CharField(label=_("الموضوع"), max_length=255)
    body = forms.CharField(
        label=_("اكتب رسالتك بالتفصيل..."), widget=forms.Textarea(attrs={"rows": 5})
    )
    attachment = forms.FileField(
        label=_("إرفاق ملف أو صورة (اختياري)"),
        required=False,
        validators=[validate_document_extension, validate_document_size],
    )
