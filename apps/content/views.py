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
        return Article.objects.filter(is_published=True).select_related("author")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = self.object

        related = Article.objects.filter(is_published=True).exclude(pk=article.pk)
        if article.category:
            related = related.filter(category=article.category)
        context["related_articles"] = related.order_by("-published_at")[:3]
        return context
