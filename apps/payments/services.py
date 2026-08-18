import uuid
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from .models import Invoice, Order, OrderItem

VAT_RATE = Decimal("0.14")


def create_order_for_item(user, item, unit_price, quantity=1):
    """Creates a fresh pending Order with a single line item — the entry
    point for "buy now"-style flows (a single course, a single booking).
    Store's cart checkout builds its Order directly since it needs
    multiple items in one go."""
    order = Order.objects.create(user=user)
    OrderItem.objects.create(
        order=order,
        content_type=ContentType.objects.get_for_model(item),
        object_id=item.pk,
        quantity=quantity,
        unit_price=unit_price,
        line_total=unit_price * quantity,
    )
    compute_order_totals(order)
    return order


def compute_order_totals(order):
    subtotal = sum((item.line_total for item in order.items.all()), Decimal(0))
    vat_amount = (subtotal * VAT_RATE).quantize(Decimal("0.01"))
    total = subtotal + vat_amount
    order.subtotal = subtotal
    order.vat_amount = vat_amount
    order.total = total
    order.save(update_fields=["subtotal", "vat_amount", "total"])
    return order


def generate_invoice(order):
    if hasattr(order, "invoice"):
        return order.invoice

    from weasyprint import HTML  # heavy import — only needed on this path

    invoice_number = f"INV-{order.pk}-{uuid.uuid4().hex[:6].upper()}"
    invoice = Invoice.objects.create(
        order=order, invoice_number=invoice_number, vat_rate=Decimal("14.00")
    )
    html = render_to_string("payments/invoice_pdf.html", {"order": order, "invoice": invoice})
    pdf_bytes = HTML(string=html).write_pdf()
    invoice.pdf_file.save(f"{invoice_number}.pdf", ContentFile(pdf_bytes), save=True)
    return invoice


def handle_payment_succeeded(payment):
    """Central fan-out for "this Order is now paid" — invoked from
    apps.payments.signals whenever a Payment's status becomes "succeeded",
    however that happens (a Paymob webhook, or an admin marking a bank
    transfer confirmed). Idempotent: a webhook retry or re-saving an
    already-paid order's Payment is a harmless no-op."""
    order = payment.order
    if order.status == "paid":
        return

    order.status = "paid"
    order.save(update_fields=["status"])

    generate_invoice(order)

    # Each of these loops order.items itself and only acts on the item
    # types it owns — safe to call unconditionally regardless of what this
    # particular order actually contains.
    from apps.bookings.services import confirm_bookings_from_paid_order
    from apps.courses.services import enroll_from_paid_order
    from apps.store.services import clear_cart_items_for_paid_order, decrement_stock_for_paid_order

    enroll_from_paid_order(order)
    confirm_bookings_from_paid_order(order)
    decrement_stock_for_paid_order(order)
    clear_cart_items_for_paid_order(order)


def handle_payment_failed(payment, reason=""):
    payment.status = "failed"
    payment.failure_reason = reason
    payment.save(update_fields=["status", "failure_reason"])
