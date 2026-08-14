from .staging import *

# Production shares staging's storage/security posture; only the values
# supplied via environment variables differ (DATABASE_URL, ALLOWED_HOSTS,
# AWS_* bucket, etc). Add production-only hardening here as it comes up
# (e.g. SECURE_SSL_REDIRECT, HSTS) in a later phase.
DEBUG = False
