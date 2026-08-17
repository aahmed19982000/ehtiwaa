from django.contrib import admin

from .models import Cart, CartItem, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "price",
        "original_price",
        "stock_quantity",
        "is_active",
        "average_rating",
    ]
    list_editable = ["price", "stock_quantity", "is_active", "average_rating"]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [ProductImageInline]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "session_key", "created_at"]
    search_fields = ["user__email", "session_key"]
    inlines = [CartItemInline]


admin.site.register(CartItem)
