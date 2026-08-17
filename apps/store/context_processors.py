from .models import CartItem


def cart(request):
    """Cart item count for the header's cart badge. Deliberately read-only —
    unlike apps.store.services.get_cart, this must NOT create a Cart (and
    thus force a session) for every anonymous visitor on every page just to
    render a header badge."""
    if request.user.is_authenticated:
        count = CartItem.objects.filter(cart__user=request.user).count()
    else:
        session_key = request.session.session_key
        count = CartItem.objects.filter(cart__session_key=session_key).count() if session_key else 0
    return {"CART_ITEMS_COUNT": count}
