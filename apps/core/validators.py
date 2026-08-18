"""Reusable upload validators.

Gemini's QA pass on the specialist "join" flow found that credential
documents (and, by the same gap, avatars and support-ticket attachments)
accepted any file of any size — including executables renamed with a
document extension, or multi-gigabyte uploads. These validators close
that gap: an extension allowlist plus a hard size cap, applied at both
the form layer (fast feedback, no disk write) and the model layer
(defense in depth against anything that bypasses the form, e.g. the
Django admin or a future API).

Extension checking alone is filename-based — it stops the obvious cases
(.exe, .php, .sh renamed to .pdf) but not a script's *content* saved with
an allowed extension (e.g. a shell script saved as "resume.pdf"). Image
uploads (avatar) already get real content verification for free — Django's
ImageField opens and verifies the file with Pillow regardless of filename,
so a non-image can't pass as one no matter what it's named. Plain
FileField uploads (credential documents, support attachments) get no such
check, which is what FileContentValidator below closes: a lightweight
magic-byte signature check against the extension the file claims to be.
It's not a substitute for antivirus scanning if these documents are ever
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

# Leading bytes real files of these types start with. .docx (and any other
# modern Office format) is a zip container — checking for the zip
# signature alone doesn't confirm it's specifically a Word document, but it
# does rule out arbitrary non-zip content (scripts, executables) claiming
# to be one.
DOCUMENT_MAGIC_BYTES = {
    ".pdf": [b"%PDF-"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    ".docx": [b"PK\x03\x04"],
}


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


@deconstructible
class FileContentValidator:
    """Rejects a file whose leading bytes don't match any known signature
    for the type its *extension* claims — e.g. a shell script saved as
    "resume.pdf" passes FileExtensionAllowlistValidator (it only reads the
    filename) but fails this, since it doesn't start with "%PDF-". Only
    checks extensions present in `magic_bytes_by_extension`; anything else
    is left to the extension allowlist alone."""

    def __init__(self, magic_bytes_by_extension):
        self.magic_bytes_by_extension = magic_bytes_by_extension

    def __eq__(self, other):
        return (
            isinstance(other, FileContentValidator)
            and self.magic_bytes_by_extension == other.magic_bytes_by_extension
        )

    def __call__(self, file):
        ext = os.path.splitext(file.name)[1].lower()
        signatures = self.magic_bytes_by_extension.get(ext)
        if not signatures:
            return
        file.seek(0)
        header = file.read(max(len(sig) for sig in signatures))
        file.seek(0)
        if not any(header.startswith(sig) for sig in signatures):
            raise ValidationError(
                _(
                    "محتوى الملف لا يطابق نوعه المعلن (%(ext)s). "
                    "برجاء التأكد من رفع الملف الصحيح."
                )
                % {"ext": ext}
            )


# Ready-to-use instances — reuse these rather than constructing new
# validators inline, so every upload field shares the same limits and
# `makemigrations` doesn't see a "different" validator on every field.
validate_document_extension = FileExtensionAllowlistValidator(DOCUMENT_EXTENSIONS)
validate_document_size = FileSizeValidator(DOCUMENT_MAX_SIZE_MB)
validate_document_content = FileContentValidator(DOCUMENT_MAGIC_BYTES)

validate_image_extension = FileExtensionAllowlistValidator(IMAGE_EXTENSIONS)
validate_image_size = FileSizeValidator(IMAGE_MAX_SIZE_MB)
