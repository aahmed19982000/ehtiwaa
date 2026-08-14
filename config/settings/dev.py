from .base import *

DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Local filesystem storage — no cloud storage backend in dev.
USE_S3 = False
