"""
URL configuration for the Ehtiwaa (احتواء) project.
"""

from allauth.urls import build_provider_urlpatterns
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="base.html"), name="home"),
    path("", include("apps.core.urls", namespace="core")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    # allauth.socialaccount.urls alone only has the generic cancel/error/signup
    # views — the actual per-provider login/callback URLs (google_login,
    # auth0_login, ...) are built separately and normally only wired up via
    # the top-level allauth.urls, which we don't include (it also mounts
    # allauth.account's own login/signup pages, which we don't use).
    path("accounts/social/", include("allauth.socialaccount.urls")),
    path("accounts/social/", include(build_provider_urlpatterns())),
    path("specialists/", include("apps.specialists.urls", namespace="specialists")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
