import json

from django.urls import reverse
from django.utils import translation
from django.views.generic import DetailView, ListView

from .models import Article


class ArticleListView(ListView):
    model = Article
    template_name = "content/list.html"
    context_object_name = "articles"
    paginate_by = 12

    def get_queryset(self):
        return (
            Article.objects.filter(is_published=True)
            .select_related("author")
            .order_by("-published_at")
        )


class ArticleDetailView(DetailView):
    model = Article
    template_name = "content/detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Article.objects.filter(is_published=True).select_related(
            "author", "author__user", "author__user__profile"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = self.object

        related = Article.objects.filter(is_published=True).exclude(pk=article.pk)
        if article.category:
            related = related.filter(category=article.category)
        context["related_articles"] = related.order_by("-published_at")[:3]
        context["structured_data"] = self._build_structured_data(article)
        return context

    def _build_structured_data(self, article):
        """JSON-LD (schema.org Article) for search engines — headline/
        description follow the same Arabic/English fallback rules the page
        itself uses, so structured data never claims content the visible
        page doesn't actually show."""

        is_arabic = translation.get_language_bidi()
        if is_arabic:
            headline = article.meta_title or article.title
            description = article.meta_description or article.title
        else:
            headline = article.meta_title_en or article.title_en or article.meta_title or article.title
            description = (
                article.meta_description_en
                or article.meta_description
                or article.title_en
                or article.title
            )

        data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": headline,
            "description": description,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": self.request.build_absolute_uri(),
            },
            "datePublished": article.published_at.isoformat() if article.published_at else None,
            "dateModified": article.updated_at.isoformat(),
            "publisher": {
                "@type": "Organization",
                "name": "احتواء",
                "logo": {
                    "@type": "ImageObject",
                    "url": self.request.build_absolute_uri("/static/img/logo2.jpg"),
                },
            },
        }

        if article.cover_image:
            data["image"] = [self.request.build_absolute_uri(article.cover_image.url)]

        if article.author:
            author_name = article.author.full_name_ar or article.author.full_name_en
            author_data = {"@type": "Person", "name": author_name}
            author_data["url"] = self.request.build_absolute_uri(
                reverse("specialists:detail", args=[article.author.pk])
            )
            avatar = getattr(getattr(article.author.user, "profile", None), "avatar", None)
            if avatar:
                author_data["image"] = self.request.build_absolute_uri(avatar.url)
            data["author"] = author_data

        if article.tags:
            data["keywords"] = ", ".join(article.tags)

        # None values (e.g. published_at on a not-yet-published preview)
        # would otherwise render as the JSON literal null, which is valid
        # but pointless noise in the markup.
        return json.dumps({k: v for k, v in data.items() if v is not None}, ensure_ascii=False)