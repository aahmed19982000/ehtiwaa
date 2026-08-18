from django.contrib.contenttypes.models import ContentType
from django.db.models import F

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


def decrement_stock_for_paid_order(order):
    """Decrements stock_quantity for every Product line item on a paid
    Order — called from apps.payments.services.handle_payment_succeeded,
    which only invokes this once per order (guarded by the order.status ==
    "paid" check upstream), so this doesn't need its own idempotency guard.

    Stock isn't reserved at add-to-cart time (see add_to_cart's docstring),
    so two customers can both have the last unit in their cart at once —
    the F()-expression UPDATE here is atomic and floors at 0 rather than
    going negative, but doesn't attempt to detect/refund an oversold order;
    that's a separate concern from "the counter must not go negative"."""
    from django.db.models.functions import Greatest

    for item in order.items.select_related("content_type"):
        if item.content_type.model_class() is not Product:
            continue
        Product.objects.filter(pk=item.object_id).update(
            stock_quantity=Greatest(F("stock_quantity") - item.quantity, 0)
        )


def create_order_from_cart(user, cart):
    """Converts the cart to a pending Order at checkout start. The cart
    itself is left untouched here — it's only cleared once payment actually
    succeeds (clear_cart_items_for_paid_order, called from
    handle_payment_succeeded), so a customer who abandons or fails payment
    finds their cart exactly as they left it instead of empty."""
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
    return order


def clear_cart_items_for_paid_order(order):
    """Removes exactly the cart rows that became this Order's Product line
    items — called once payment succeeds, not at checkout start. Scoped to
    matching product ids (not "empty the whole cart") so anything the
    customer added after starting this checkout, for a different product,
    survives."""
    cart = Cart.objects.filter(user=order.user).first()
    if cart is None:
        return
    product_ids = [
        item.object_id
        for item in order.items.select_related("content_type")
        if item.content_type.model_class() is Product
    ]
    if product_ids:
        cart.items.filter(product_id__in=product_ids).delete()
