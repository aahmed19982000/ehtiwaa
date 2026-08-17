from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q

from .models import FAQItem


def search_faqs(query, limit=8):
    """Instant FAQ search backed by the GIN-indexed search_vector, unioned
    with a plain icontains match. The union matters for a live as-you-type
    box specifically: full-text search matches whole lexemes, so a partial
    prefix typed mid-word (e.g. "حج" before finishing "حجز") wouldn't match
    until the word is complete, while icontains catches it immediately."""
    query = (query or "").strip()
    if not query:
        return FAQItem.objects.none()

    search_query = SearchQuery(query, config="simple")
    return (
        FAQItem.objects.filter(
            Q(search_vector=search_query)
            | Q(question__icontains=query)
            | Q(answer__icontains=query)
        )
        .annotate(rank=SearchRank("search_vector", search_query))
        .order_by("-rank", "order")[:limit]
    )
