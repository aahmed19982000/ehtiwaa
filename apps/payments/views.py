import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from . import paymob
from .forms import PaymentMethodForm
from .models import Order, Payment
from .services import handle_payment_failed

logger = logging.getLogger(__name__)


class CheckoutView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    template_name = "payments/checkout.html"

    def get_order(self, request, order_id):
        return get_object_or_404(
            Order.objects.prefetch_related("items"),
            pk=order_id,
            user=request.user,
            status="pending",
        )

    def build_context(self, order, form):
        last_payment = order.payments.first()  # Payment.Meta.ordering = -created_at
        return {
            "order": order,
            "form": form,
            "last_payment_failed": bool(last_payment and last_payment.status == "failed"),
            "last_payment": last_payment,
            "card_available": paymob.is_configured(),
        }

    def get(self, request, order_id):
        order = self.get_order(request, order_id)
        form = PaymentMethodForm()
        return render(request, self.template_name, self.build_context(order, form))

    def post(self, request, order_id):
        order = self.get_order(request, order_id)
        form = PaymentMethodForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self.build_context(order, form))

        method = form.cleaned_data["method"]

        if method == "bank_transfer":
            Payment.objects.create(order=order, method="bank_transfer", status="initiated")
            return redirect("payments:bank-transfer-pending", order_id=order.pk)

        # method == "card"
        if not paymob.is_configured():
            messages.error(
                request,
                _("الدفع بالبطاقة غير مُفعّل حاليًا — برجاء استخدام التحويل البنكي."),
            )
            return render(request, self.template_name, self.build_context(order, form))

        try:
            iframe_url, paymob_order_id = paymob.start_card_payment(order)
        except paymob.PaymobError as exc:
            logger.error("Paymob checkout start failed for order %s: %s", order.pk, exc)
            payment = Payment.objects.create(
                order=order, method="card", status="failed", failure_reason=str(exc)
            )
            handle_payment_failed(payment, str(exc))
            messages.error(request, _("تعذّر بدء عملية الدفع. برجاء المحاولة مرة أخرى."))
            return render(request, self.template_name, self.build_context(order, form))

        Payment.objects.create(
            order=order, method="card", status="initiated", provider_reference=str(paymob_order_id)
        )
        return redirect(iframe_url)


class BankTransferPendingView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    template_name = "payments/bank_transfer_pending.html"

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, user=request.user)
        return render(
            request,
            self.template_name,
            {
                "order": order,
                "BANK_TRANSFER_BANK_NAME": settings.BANK_TRANSFER_BANK_NAME,
                "BANK_TRANSFER_ACCOUNT_NAME": settings.BANK_TRANSFER_ACCOUNT_NAME,
                "BANK_TRANSFER_ACCOUNT_NUMBER": settings.BANK_TRANSFER_ACCOUNT_NUMBER,
                "BANK_TRANSFER_IBAN": settings.BANK_TRANSFER_IBAN,
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymobWebhookView(View):
    """Server-to-server "transaction processed" callback — not a browser
    request, so no CSRF token and no login. Authenticity is guaranteed
    entirely by the HMAC signature, not by who's calling."""

    def post(self, request):
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return HttpResponseForbidden("invalid payload")

        transaction_data = payload.get("obj", payload)
        received_hmac = request.GET.get("hmac", "")
        if not paymob.verify_webhook_signature(transaction_data, received_hmac):
            logger.warning("Paymob webhook rejected: bad HMAC signature")
            return HttpResponseForbidden("invalid signature")

        paymob_order_id = str(transaction_data.get("order", {}).get("id", ""))
        payment = (
            Payment.objects.filter(provider_reference=paymob_order_id, method="card")
            .order_by("-created_at")
            .first()
        )
        if not payment:
            logger.warning("Paymob webhook: no Payment found for order id %s", paymob_order_id)
            return HttpResponse(status=200)  # ack anyway — nothing to retry

        if transaction_data.get("success"):
            payment.status = "succeeded"
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at"])  # triggers apps.payments.signals
        else:
            reason = transaction_data.get("data", {}).get("message", "")
            handle_payment_failed(payment, reason or _("تم رفض البطاقة من البنك المُصدر."))

        return HttpResponse(status=200)
