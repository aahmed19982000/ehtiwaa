from django import forms
from django.utils.translation import gettext_lazy as _

from .models import RATING_CHOICES


class ReviewForm(forms.Form):
    rating = forms.ChoiceField(label=_("التقييم"), choices=RATING_CHOICES, widget=forms.RadioSelect)
    comment = forms.CharField(
        label=_("تعليقك (اختياري)"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
