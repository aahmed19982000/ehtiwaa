from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="list"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path(
        "cart/items/<int:item_id>/update/",
        views.CartItemUpdateView.as_view(),
        name="cart-item-update",
    ),
    path("cart/checkout/", views.CartCheckoutView.as_view(), name="cart-checkout"),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="detail"),
    path("<slug:slug>/add/", views.CartAddView.as_view(), name="cart-add"),
]
