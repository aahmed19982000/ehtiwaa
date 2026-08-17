"""
Base Django settings for the Ehtiwaa (احتواء) project, shared by all environments.
Environment-specific overrides live in dev.py / staging.py / production.py.
"""

from pathlib import Path

import environ

# BASE_DIR is the repo root: config/settings/base.py -> config/settings -> config -> repo root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
    # Auth0 (Google + Database connection) is the only public signup/login
    # path — allauth.account itself is still unused (see ACCOUNT_EMAIL_VERIFICATION
    # below), Django admin keeps its own separate ModelBackend password login.
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.auth0",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.specialists",
    "apps.bookings",
    "apps.courses",
    "apps.store",
    "apps.payments",
    "apps.content",
    "apps.forum",
    "apps.assessments",
    "apps.matchfinder",
    "apps.support",
    "apps.reviews",
    "apps.notifications",
    "apps.dashboard",
    "apps.adminpanel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.core.middleware.ClientTimezoneMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.language_urls",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_USER_MODEL = "accounts.User"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "home"

# Social login (Google, Auth0) — buttons only render once these are set;
# see docs/social-login-setup.md for how to obtain them.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
AUTH0_DOMAIN = env("AUTH0_DOMAIN", default="")
AUTH0_CLIENT_ID = env("AUTH0_CLIENT_ID", default="")
AUTH0_CLIENT_SECRET = env("AUTH0_CLIENT_SECRET", default="")
# Database connection used for our own signup form (apps.accounts.auth0),
# which talks to Auth0's Authentication API directly instead of redirecting
# to the hosted Universal Login page. Requires the "Password" grant type
# enabled on the Auth0 application — see docs/social-login-setup.md.
AUTH0_DB_CONNECTION = env("AUTH0_DB_CONNECTION", default="Username-Password-Authentication")

# Google Calendar — creates a Meet link for each booking (apps.bookings).
# Booking creation degrades gracefully (no link, just logs) when unset. Uses
# a real Google account's OAuth refresh token (not a service account) —
# Google Meet auto-creation via the API isn't available to plain service
# accounts. Run `python manage.py google_calendar_authorize` once to obtain
# GOOGLE_CALENDAR_REFRESH_TOKEN — see apps/bookings/management/commands/.
GOOGLE_CALENDAR_CLIENT_ID = env("GOOGLE_CALENDAR_CLIENT_ID", default="")
GOOGLE_CALENDAR_CLIENT_SECRET = env("GOOGLE_CALENDAR_CLIENT_SECRET", default="")
GOOGLE_CALENDAR_REFRESH_TOKEN = env("GOOGLE_CALENDAR_REFRESH_TOKEN", default="")
GOOGLE_CALENDAR_ID = env("GOOGLE_CALENDAR_ID", default="") or "primary"

SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.EhtiwaaSocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
# Skip allauth's "you're about to log in with a third-party account" interstitial
# — clicking the button goes straight to the provider (still full OAuth underneath).
SOCIALACCOUNT_LOGIN_ON_GET = True
# We don't include allauth.account.urls (Auth0 hosts its own signup/login/
# verification pages). Without this, allauth's account app tries to send its
# own confirmation email on signup and fails with NoReverseMatch on
# 'account_confirm_email', which doesn't exist in our URLconf. Auth0 already
# handles email verification itself, so allauth's own step is redundant here.
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": (
            [
                {
                    "client_id": GOOGLE_CLIENT_ID,
                    "secret": GOOGLE_CLIENT_SECRET,
                    "key": "",
                }
            ]
            if GOOGLE_CLIENT_ID
            else []
        ),
        "SCOPE": ["profile", "email"],
    },
    "auth0": {
        "AUTH0_URL": f"https://{AUTH0_DOMAIN}" if AUTH0_DOMAIN else "",
        "APPS": (
            [
                {
                    "client_id": AUTH0_CLIENT_ID,
                    "secret": AUTH0_CLIENT_SECRET,
                    "key": "",
                }
            ]
            if AUTH0_DOMAIN and AUTH0_CLIENT_ID
            else []
        ),
    },
}

# MinimumLengthValidator must match this Auth0 tenant's actual Database
# connection password policy (Authentication > Database > Password Policy)
# — otherwise a password we accept here still gets rejected later by Auth0's
# API with a confusing error. Currently 8; if you lower/raise this, update
# the connection's policy in the Auth0 dashboard to match.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Egypt is the confirmed target market (RTL Arabic content, EGP currency, 14% VAT).
# Arabic stays the default/unprefixed language (see i18n_patterns in config/urls.py);
# English is available under the /en/ prefix for non-Arabic-speaking users.
LANGUAGE_CODE = "ar"
LANGUAGES = [
    ("ar", "العربية"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

# Static & media files
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email (values supplied per-environment via .env / real env vars)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@ehtiwaa.example")

# No SMTP host configured (typical for local dev) -> print emails to the
# runserver console instead of failing to send.
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
