# Seeds the single HomepageContent row with the homepage's current
# hardcoded hero copy, so the panel's hero-edit form has real starting
# content instead of blank fields, and HomeView never has to handle a
# missing row.
from django.db import migrations

HERO_TITLE = "محتوى موثوق، دورات، واستشارات متخصصة في مكان واحد"
HERO_SUBTITLE = (
    "منصة عربية تجمع المقالات التوعوية والدورات التدريبية والجلسات "
    "الاستشارية مع أخصائيين معتمدين، بخطوات واضحة من الاختيار إلى الحجز."
)


def seed_homepage_content(apps, schema_editor):
    HomepageContent = apps.get_model("core", "HomepageContent")
    if not HomepageContent.objects.exists():
        HomepageContent.objects.create(hero_title=HERO_TITLE, hero_subtitle=HERO_SUBTITLE)


def remove_homepage_content(apps, schema_editor):
    HomepageContent = apps.get_model("core", "HomepageContent")
    HomepageContent.objects.filter(hero_title=HERO_TITLE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_homepagecontent"),
    ]

    operations = [
        migrations.RunPython(seed_homepage_content, remove_homepage_content),
    ]
