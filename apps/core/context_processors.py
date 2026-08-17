from django.urls import NoReverseMatch, reverse
from django.utils import translation


def language_urls(request):
    """The current page's URL re-rendered under each supported language.

    Used by the header's AR/EN switcher. We deliberately don't rely on
    django.urls.translate_url()/the set_language view for this: with
    i18n_patterns(prefix_default_language=False), translate_url() re-resolves
    the target path with django.urls.resolve(), which only matches the
    *currently active* language's own prefix — for the unprefixed default
    (Arabic) that's an empty prefix, so resolving an incoming "/en/..." path
    fails and translate_url() silently returns the URL unchanged. Since we
    already have the correctly resolved view for *this* request (via
    request.resolver_match), we can just re-reverse it per language directly,
    which sidesteps that resolve() step entirely.
    """
    match = request.resolver_match
    urls = {}
    for code, _label in [("ar", "العربية"), ("en", "English")]:
        if match is None:
            urls[code] = "/" if code == "ar" else "/en/"
            continue
        view_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
        with translation.override(code):
            try:
                urls[code] = reverse(view_name, args=match.args, kwargs=match.kwargs)
            except NoReverseMatch:
                urls[code] = "/" if code == "ar" else "/en/"
    return {"LANGUAGE_URLS": urls}
