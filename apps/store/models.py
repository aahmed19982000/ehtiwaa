from django.db import models

from apps.core.models import TimeStampedModel


class Product(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Cart(TimeStampedModel):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="cart")

    def __str__(self):
        return f"Cart<{self.user_id}>"


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
