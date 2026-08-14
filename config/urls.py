"""
URL configuration for the Ehtiwaa (احتواء) project.

Phase 1.1 only needs a minimal shell route to verify the base template
(RTL layout, header/footer, static assets) renders correctly. Real
application routes are added per-app starting in later phases.
"""

from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="base.html"), name="home"),
]
