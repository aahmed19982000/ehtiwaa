from django import forms
from django.utils.translation import gettext_lazy as _


class BookingForm(forms.Form):
    date = forms.DateField(widget=forms.HiddenInput)
    time_slot = forms.ChoiceField(label=_("اختر الموعد"), widget=forms.RadioSelect)
    contact_phone = forms.CharField(label=_("رقم للتواصل"), max_length=20)
    notes = forms.CharField(
        label=_("ملاحظات (اختياري)"), required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, available_slots=(), **kwargs):
        super().__init__(*args, **kwargs)
        # Only slots the service currently reports as free are valid
        # choices — ChoiceField rejects anything else server-side, so a
        # tampered/stale "booked" value can't be submitted.
        self.fields["time_slot"].choices = [
            (slot["value"], slot["label"]) for slot in available_slots if slot["status"] == "available"
        ]
