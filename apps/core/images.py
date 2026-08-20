"""Shared upload-image compression — the one place that decides how
aggressively images get resized/re-encoded, used by every model with an
image field (see TimeStampedModel.save() in apps/core/models.py) and by
the article body editor's inline-image upload endpoint
(apps.adminpanel.views.ArticleImageUploadView), which saves straight to
storage instead of through a model.
"""

import io

from PIL import Image

MAX_DIMENSION = 1920
JPEG_QUALITY = 82
WEBP_QUALITY = 82


def compress_image_bytes(file_obj, max_dimension=MAX_DIMENSION):
    """Returns re-encoded image bytes (or None if nothing worth changing)
    for any file-like object Pillow can open. Never raises — an image it
    can't process (unsupported format, corrupt file, already handled
    elsewhere by Django's own ImageField validation) is left alone rather
    than blocking the save; compression is a nice-to-have, not a
    correctness requirement."""

    try:
        file_obj.seek(0)
        image = Image.open(file_obj)
        image.load()
    except Exception:
        return None

    image_format = (image.format or "").upper()
    if image_format not in ("JPEG", "PNG", "WEBP"):
        return None

    if image_format == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    if image.width > max_dimension or image.height > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buffer = io.BytesIO()
    save_kwargs = {"optimize": True}
    if image_format in ("JPEG", "WEBP"):
        save_kwargs["quality"] = JPEG_QUALITY if image_format == "JPEG" else WEBP_QUALITY
    image.save(buffer, format=image_format, **save_kwargs)

    original_size = getattr(file_obj, "size", None)
    if original_size is not None and buffer.tell() >= original_size:
        # Re-encoding came out larger (e.g. an already-optimized PNG) —
        # keep the original rather than making the file bigger.
        return None

    buffer.seek(0)
    return buffer.read()


def compress_image_field(image_field_file, max_dimension=MAX_DIMENSION):
    """Compresses `image_field_file` in place, but only if it's a freshly
    uploaded file not yet written to storage (`_committed` is Django's own
    flag for exactly that) — an image already on disk from a previous save
    is left untouched rather than being re-compressed on every unrelated
    edit to the row."""

    if not image_field_file or getattr(image_field_file, "_committed", True):
        return

    from django.core.files.base import ContentFile

    compressed = compress_image_bytes(image_field_file, max_dimension=max_dimension)
    if compressed is None:
        image_field_file.seek(0)
        return

    name = image_field_file.name
    image_field_file.save(name, ContentFile(compressed), save=False)
