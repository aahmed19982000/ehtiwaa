from django import forms
from django.utils.translation import gettext_lazy as _


class AskQuestionForm(forms.Form):
    title = forms.CharField(label=_("عنوان السؤال"), max_length=255)
    body = forms.CharField(label=_("تفاصيل السؤال"), widget=forms.Textarea(attrs={"rows": 5}))
    tags = forms.CharField(label=_("الوسوم (افصل بينها بفاصلة)"), required=False, max_length=255)

    def clean_tags(self):
        raw = self.cleaned_data.get("tags", "")
        return [t.strip() for t in raw.split(",") if t.strip()]


class AnswerForm(forms.Form):
    body = forms.CharField(label=_("إجابتك"), widget=forms.Textarea(attrs={"rows": 4}))


class ReportForm(forms.Form):
    reason = forms.CharField(
        label=_("سبب الإبلاغ (اختياري)"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
