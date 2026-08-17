from django import forms
from django.utils.translation import gettext_lazy as _


class PaymentMethodForm(forms.Form):
    # Apple Pay appears in the design but needs its own Apple
    # Merchant/Developer setup to actually work — not offered until that
    # exists. "mada" (Payment.METHOD_CHOICES) is a Saudi network, not
    # relevant for an Egypt-only platform, so it's not offered either.
    METHOD_CHOICES = [
        ("card", _("بطاقة ائتمان (فيزا / ماستركارد)")),
        ("bank_transfer", _("تحويل بنكي")),
    ]
    method = forms.ChoiceField(choices=METHOD_CHOICES, widget=forms.RadioSelect, initial="card")
