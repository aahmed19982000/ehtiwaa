from django.contrib import admin

from .models import Invoice, Order, OrderItem, Payment

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Invoice)
