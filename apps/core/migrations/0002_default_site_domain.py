from django.conf import settings
from django.db import migrations


def set_site_domain(apps, schema_editor):
    """django.contrib.sites (required by allauth) seeds SITE_ID=1 with
    domain "example.com" — left as-is, password-reset/activation emails
    would link to a dead domain. Point it at something sane per
    environment; staging/production should update this via /admin/ or
    override ALLOWED_HOSTS[0]-based value once a real domain exists."""
    Site = apps.get_model("sites", "Site")
    domain = "localhost:8000" if settings.DEBUG else (settings.ALLOWED_HOSTS or ["example.com"])[0]
    Site.objects.filter(pk=settings.SITE_ID).update(domain=domain, name="احتواء")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0002_alter_domain_unique"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(set_site_domain, noop),
    ]
