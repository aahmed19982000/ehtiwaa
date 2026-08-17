from django import forms
from django.utils.translation import gettext_lazy as _


class ReviewDecisionForm(forms.Form):
    notes = forms.CharField(
        label=_("ملاحظات (اختياري)"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
