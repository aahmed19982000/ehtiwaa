from django.contrib import admin

from .models import Cart, CartItem, Product

admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
