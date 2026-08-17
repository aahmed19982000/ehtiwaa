from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/<int:order_id>/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "checkout/<int:order_id>/bank-transfer/",
        views.BankTransferPendingView.as_view(),
        name="bank-transfer-pending",
    ),
]
