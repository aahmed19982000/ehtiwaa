from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("", views.SupportHomeView.as_view(), name="home"),
    path("search/", views.FaqSearchView.as_view(), name="faq-search"),
    path("ticket/", views.TicketCreateView.as_view(), name="ticket-create"),
    path("category/<slug:slug>/", views.CategoryDetailView.as_view(), name="category"),
]
