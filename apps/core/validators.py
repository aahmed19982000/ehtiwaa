"""Reusable upload validators.

Gemini's QA pass on the specialist "join" flow found that credential
documents (and, by the same gap, avatars and support-ticket attachments)
accepted any file of any size — including executables renamed with a
document extension, or multi-gigabyte uploads. These validators close
that gap: an extension allowlist plus a hard size cap, applied at both
the form layer (fast feedback, no disk write) and the model layer
(defense in depth against anything that bypasses the form, e.g. the
Django admin or a future API).

Extension checking here is filename-based, not content-sniffing/magic-byte
based — it stops the obvious cases (.exe, .php, .sh renamed to .pdf) but
is not a substitute for antivirus scanning if these documents are ever
treated as trusted/executed server-side.
"""

import os

from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

DOCUMENT_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

DOCUMENT_MAX_SIZE_MB = 10
IMAGE_MAX_SIZE_MB = 5


@deconstructible
class FileSizeValidator:
    """Rejects an uploaded file over `max_size_mb` megabytes.

    `@deconstructible` lets Django serialize this into a migration when
    used on a model field (instead of erroring on `makemigrations`).
    """

    def __init__(self, max_size_mb):
        self.max_size_mb = max_size_mb

    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_size_mb == other.max_size_mb

    def __call__(self, file):
        max_bytes = self.max_size_mb * 1024 * 1024
        if file.size > max_bytes:
            raise ValidationError(
                _("حجم الملف كبير جدًا (%(size)s). الحد الأقصى المسموح به %(max)s ميجابايت.")
                % {"size": filesizeformat(file.size), "max": self.max_size_mb}
            )


@deconstructible
class FileExtensionAllowlistValidator:
    """Rejects an uploaded file whose extension isn't in `allowed_extensions`."""

    def __init__(self, allowed_extensions):
        self.allowed_extensions = [ext.lower() for ext in allowed_extensions]

    def __eq__(self, other):
        return (
            isinstance(other, FileExtensionAllowlistValidator)
            and self.allowed_extensions == other.allowed_extensions
        )

    def __call__(self, file):
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.allowed_extensions:
            raise ValidationError(
                _("نوع الملف غير مدعوم. الأنواع المسموح بها: %(extensions)s")
                % {"extensions": ", ".join(self.allowed_extensions)}
            )


# Ready-to-use instances — reuse these rather than constructing new
# validators inline, so every upload field shares the same limits and
# `makemigrations` doesn't see a "different" validator on every field.
validate_document_extension = FileExtensionAllowlistValidator(DOCUMENT_EXTENSIONS)
validate_document_size = FileSizeValidator(DOCUMENT_MAX_SIZE_MB)

validate_image_extension = FileExtensionAllowlistValidator(IMAGE_EXTENSIONS)
validate_image_size = FileSizeValidator(IMAGE_MAX_SIZE_MB)
