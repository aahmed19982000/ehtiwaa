from .base import *

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Cloud (S3-compatible) storage for user-uploaded media. Static files stay
# server-local (served via collectstatic + a reverse proxy/CDN in front of
# the app), only MEDIA is routed through object storage.
USE_S3 = env.bool("USE_S3", default=True)

if USE_S3:
    INSTALLED_APPS += ["storages"]

    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
    # Set for S3-compatible providers like DigitalOcean Spaces; leave unset for AWS S3 itself.
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
