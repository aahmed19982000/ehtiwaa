from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.payments.services import create_order_for_item, handle_payment_succeeded

from .models import Cart, CartItem, Product
from .services import create_order_from_cart

User = get_user_model()


class StockDecrementOnPaidOrderTests(TestCase):
    """Confirmed via QA that stock_quantity was never decremented anywhere
    in the codebase — apps.store.services.decrement_stock_for_paid_order
    closes that gap, wired into
    apps.payments.services.handle_payment_succeeded."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="whatever-123"
        )
        self.product = Product.objects.create(
            name="Breathing cards",
            slug="breathing-cards",
            price=Decimal("89.00"),
            stock_quantity=5,
        )

    def _pay(self, order):
        payment = order.payments.create(method="card", status="initiated")
        payment.status = "succeeded"
        payment.save(update_fields=["status"])
        handle_payment_succeeded(payment)

    def test_stock_decremented_by_purchased_quantity(self):
        order = create_order_for_item(self.user, self.product, self.product.price, quantity=2)
        self._pay(order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

    def test_stock_floors_at_zero_instead_of_going_negative(self):
        order = create_order_for_item(self.user, self.product, self.product.price, quantity=8)
        self._pay(order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0)

    def test_paying_twice_does_not_double_decrement(self):
        order = create_order_for_item(self.user, self.product, self.product.price, quantity=2)
        self._pay(order)
        # handle_payment_succeeded is idempotent on an already-paid order —
        # a webhook retry must not decrement stock a second time.
        payment = order.payments.first()
        handle_payment_succeeded(payment)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)


class CartSurvivesAbandonedCheckoutTests(TestCase):
    """Reported bug: going back to the cart after starting checkout but not
    completing payment showed an empty cart. create_order_from_cart used to
    delete cart.items immediately at checkout start; the cart is now only
    cleared once payment actually succeeds."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="cart-buyer", email="cart-buyer@example.com", password="whatever-123"
        )
        self.product = Product.objects.create(
            name="Mood journal", slug="mood-journal-2", price=Decimal("144.00"), stock_quantity=10
        )
        self.other_product = Product.objects.create(
            name="Breathing cards 2",
            slug="breathing-cards-2",
            price=Decimal("89.00"),
            stock_quantity=10,
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_cart_item_survives_checkout_start(self):
        create_order_from_cart(self.user, self.cart)
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_cart_item_cleared_only_after_payment_succeeds(self):
        order = create_order_from_cart(self.user, self.cart)
        self.assertTrue(CartItem.objects.filter(pk=self.cart_item.pk).exists())

        payment = order.payments.create(method="card", status="initiated")
        payment.status = "succeeded"
        payment.save(update_fields=["status"])
        handle_payment_succeeded(payment)

        self.assertFalse(CartItem.objects.filter(pk=self.cart_item.pk).exists())

    def test_unrelated_cart_items_added_after_checkout_start_are_untouched(self):
        order = create_order_from_cart(self.user, self.cart)
        # Added after this checkout's Order already exists — a genuinely
        # separate cart addition, not part of what's being paid for.
        later_item = CartItem.objects.create(cart=self.cart, product=self.other_product, quantity=1)

        payment = order.payments.create(method="card", status="initiated")
        payment.status = "succeeded"
        payment.save(update_fields=["status"])
        handle_payment_succeeded(payment)

        self.assertFalse(CartItem.objects.filter(pk=self.cart_item.pk).exists())
        self.assertTrue(CartItem.objects.filter(pk=later_item.pk).exists())
