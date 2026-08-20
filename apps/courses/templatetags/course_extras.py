import re

from django import template

register = template.Library()

# Matches any of the usual ways staff might paste a YouTube link:
# watch?v=, youtu.be/, /shorts/, or an already-embeddable /embed/ URL.
_YOUTUBE_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtube\.com/shorts/|youtu\.be/|youtube\.com/embed/)"
    r"([\w-]{11})"
)

# Bunny Stream's dashboard "share" link uses /play/<library>/<video>, but only
# /embed/<library>/<video> actually renders inside an <iframe> — both forms
# use the same ids, so this just swaps the path.
_BUNNY_RE = re.compile(r"iframe\.mediadelivery\.net/(?:play|embed)/(\d+)/([\w-]+)")


@register.filter
def video_embed_url(url):
    """Normalizes a staff-pasted YouTube or Bunny Stream URL into a URL
    that's safe to drop straight into an <iframe src="...">. Anything else
    is passed through unchanged (already-embeddable link, or unsupported
    provider — the template falls back to a plain link in that case)."""
    if not url:
        return ""

    youtube_match = _YOUTUBE_RE.search(url)
    if youtube_match:
        return f"https://www.youtube.com/embed/{youtube_match.group(1)}"

    bunny_match = _BUNNY_RE.search(url)
    if bunny_match:
        library_id, video_id = bunny_match.groups()
        return f"https://iframe.mediadelivery.net/embed/{library_id}/{video_id}"

    return url


@register.filter
def is_embeddable_video(url):
    if not url:
        return False
    return bool(_YOUTUBE_RE.search(url) or _BUNNY_RE.search(url) or "mediadelivery.net" in url)


@register.filter
def hours_minutes(total_minutes):
    """Splits a minute count into {hours, minutes} for duration display —
    kept as a filter (not a model property) so the "X ساعة Y دقيقة" copy
    stays translatable in the template instead of hardcoded in Python."""
    try:
        total_minutes = int(total_minutes or 0)
    except (TypeError, ValueError):
        total_minutes = 0
    hours, minutes = divmod(total_minutes, 60)
    return {"hours": hours, "minutes": minutes}
