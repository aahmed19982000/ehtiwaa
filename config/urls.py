"""
URL configuration for the Ehtiwaa (احتواء) project.
"""

from allauth.urls import build_provider_urlpatterns
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from apps.accounts.views import Auth0RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # {% url 'set_language' %} — POSTed to by the language switcher in the header.
    path("i18n/", include("django.conf.urls.i18n")),
    # OAuth callback paths stay under /accounts/social/ — this exact prefix is
    # already registered as the Allowed Callback URL in the Auth0/Google
    # dashboards, so it must not change independently of those, and must stay
    # outside i18n_patterns (no /en/ or /ar/ prefix).
    # allauth.socialaccount.urls alone only has the generic cancel/error/signup
    # views — the actual per-provider login/callback URLs (google_login,
    # auth0_login, ...) are built separately and normally only wired up via
    # the top-level allauth.urls, which we don't include (it also mounts
    # allauth.account's own login/signup pages, which we don't use).
    path("accounts/social/", include("allauth.socialaccount.urls")),
    path("accounts/social/", include(build_provider_urlpatterns())),
    # allauth's built-in "login cancelled"/"login error" pages (shown when
    # Auth0 comes back with an OAuth error, e.g. the user backs out) always
    # try to reverse() a URL named 'account_login' — normally provided by
    # allauth.account.urls, which we don't include since Auth0 is our only
    # login page. Without this, those two pages 500 with NoReverseMatch.
    path("accounts/login/", Auth0RedirectView.as_view(), name="account_login"),
]

# Arabic (the default LANGUAGE_CODE) stays unprefixed so existing /login/,
# /signup/, etc. URLs keep working; English is served under /en/.
urlpatterns += i18n_patterns(
    path("", TemplateView.as_view(template_name="base.html"), name="home"),
    path("", include("apps.core.urls", namespace="core")),
    # Mounted at root (not /accounts/) for short user-facing URLs — /signup/,
    # /login/, /profile/, etc.
    path("", include("apps.accounts.urls", namespace="accounts")),
    # /specialists/ hosts both the public directory (/specialists/,
    # /specialists/<pk>/) and the "join as a specialist" flow
    # (/specialists/join/...) — see apps/specialists/urls.py.
    path("specialists/", include("apps.specialists.urls", namespace="specialists")),
    path("bookings/", include("apps.bookings.urls", namespace="bookings")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
