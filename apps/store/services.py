from django.contrib.contenttypes.models import ContentType

from apps.payments.models import Order, OrderItem
from apps.payments.services import compute_order_totals

from .models import Cart, CartItem, Product


def get_cart(request):
    """Resolves the current visitor's cart — the logged-in user's cart if
    authenticated, otherwise a session-scoped cart. There's deliberately no
    merge-on-login: a guest cart stays tied to that session even after the
    visitor signs in (out of scope for this phase)."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    if not request.session.session_key:
        request.session.save()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def add_to_cart(cart, product, quantity=1):
    """Adds `quantity` of product to the cart, clamped to available stock.
    Returns the resulting CartItem, or None if the clamped total is 0 (e.g.
    the product is out of stock) — in which case no row is left behind."""
    item, _created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={"quantity": 0}
    )
    item.quantity = max(min(item.quantity + quantity, product.stock_quantity), 0)
    if item.quantity == 0:
        item.delete()
        return None
    item.save(update_fields=["quantity"])
    return item


def set_cart_item_quantity(item, quantity):
    """Sets an existing CartItem's quantity outright (vs. add_to_cart's
    increment), clamped to stock. quantity <= 0 removes the row."""
    item.quantity = max(min(quantity, item.product.stock_quantity), 0)
    if item.quantity == 0:
        item.delete()
        return None
    item.save(update_fields=["quantity"])
    return item


def create_order_from_cart(user, cart):
    """Converts the cart to a pending Order — a one-way conversion at
    checkout start (standard e-commerce pattern), not at payment success.
    If the customer abandons payment the Order just stays pending; the
    cart is already empty either way."""
    order = Order.objects.create(user=user)
    content_type = ContentType.objects.get_for_model(Product)
    for cart_item in cart.items.select_related("product"):
        OrderItem.objects.create(
            order=order,
            content_type=content_type,
            object_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.product.price,
            line_total=cart_item.line_total,
        )
    compute_order_totals(order)
    cart.items.all().delete()
    return order
