from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("paid", "paid"),
        ("cancelled", "cancelled"),
        ("refunded", "refunded"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order<{self.pk}>"


class OrderItem(TimeStampedModel):
    """A single line in an Order. `item` points at whatever was purchased —
    a courses.Course, store.Product, or bookings.Booking — via a generic
    relation, so Order doesn't need three separate item models."""

    order = models.ForeignKey("payments.Order", on_delete=models.CASCADE, related_name="items")
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, related_name="+")
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"OrderItem<{self.order_id}>"


class Payment(TimeStampedModel):
    METHOD_CHOICES = [
        ("card", "card"),
        ("mada", "mada"),
        ("apple_pay", "apple_pay"),
        ("bank_transfer", "bank_transfer"),
    ]
    STATUS_CHOICES = [
        ("initiated", "initiated"),
        ("succeeded", "succeeded"),
        ("failed", "failed"),
        ("refunded", "refunded"),
    ]

    # FK, not OneToOne — "إعادة المحاولة" (retry after a failed payment)
    # means a second Payment attempt against the same Order, not a second
    # Order. The most recent attempt is what the checkout page shows.
    order = models.ForeignKey("payments.Order", on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")
    provider_reference = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment<{self.order_id}>"


class Invoice(TimeStampedModel):
    order = models.OneToOneField("payments.Order", on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=100, unique=True)
    # Egypt VAT rate confirmed at 14% in the approved technical report.
    vat_rate = models.DecimalField(max_digits=4, decimal_places=2, default=14.00)
    pdf_file = models.FileField(upload_to="invoices/", null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number
