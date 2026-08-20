# Converts the old free-text Article.category into real Category rows,
# linking each article to the matching one via the new FK field added in
# 0006. Runs before the old CharField is dropped in 0008.
from django.db import migrations


def migrate_categories(apps, schema_editor):
    Article = apps.get_model("content", "Article")
    Category = apps.get_model("content", "Category")

    names = Article.objects.exclude(category="").values_list("category", flat=True).distinct()
    name_to_category = {}
    for name in names:
        category, _ = Category.objects.get_or_create(name=name)
        name_to_category[name] = category

    for article in Article.objects.exclude(category=""):
        article.category_new = name_to_category[article.category]
        article.save(update_fields=["category_new"])


def reverse_migrate_categories(apps, schema_editor):
    Article = apps.get_model("content", "Article")

    for article in Article.objects.exclude(category_new__isnull=True):
        article.category = article.category_new.name
        article.save(update_fields=["category"])


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_category"),
    ]

    operations = [
        migrations.RunPython(migrate_categories, reverse_migrate_categories),
    ]
