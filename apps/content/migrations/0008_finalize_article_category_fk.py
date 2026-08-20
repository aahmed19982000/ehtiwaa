from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0007_migrate_category_data"),
    ]

    operations = [
        migrations.RemoveField(model_name="article", name="category"),
        migrations.RenameField(model_name="article", old_name="category_new", new_name="category"),
    ]
