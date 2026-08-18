from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from apps.core.models import TimeStampedModel


class Product(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    # Free-text grouping shown on the catalog/breadcrumb — no category
    # catalog exists yet, same simplification as courses.Course.category.
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Pre-discount price shown struck through — blank when not discounted.
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    # Cover image used on the catalog grid; the detail page's gallery comes
    # from ProductImage below (falls back to this if none are set).
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Recomputed automatically by apps.reviews' post_save/post_delete
    # signal whenever a Review targets this product.
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    # See apps/specialists/models.py Specialist.reviews for why this is
    # needed — without it, deleting a Product leaves orphaned Review rows.
    reviews = GenericRelation("reviews.Review", related_query_name="product")

    def __str__(self):
        return self.name

    @property
    def discount_percent(self):
        if not self.original_price or self.original_price <= self.price:
            return 0
        return round((1 - self.price / self.original_price) * 100)

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0


class ProductImage(TimeStampedModel):
    product = models.ForeignKey("store.Product", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/gallery/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"ProductImage<{self.product_id}>"


class Cart(TimeStampedModel):
    # Exactly one of these identifies the cart's owner: a logged-in user's
    # cart follows them across devices, an anonymous visitor's cart is
    # scoped to their session. See apps.store.services.get_cart — there's
    # deliberately no merge-on-login here (out of scope for this phase).
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="cart"
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name="store_cart_has_user_or_session",
            )
        ]

    def __str__(self):
        return f"Cart<{self.user_id or self.session_key}>"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey("store.Cart", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "store.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("cart", "product")]

    def __str__(self):
        return f"CartItem<{self.cart_id}:{self.product_id}>"

    @property
    def line_total(self):
        return self.product.price * self.quantity
