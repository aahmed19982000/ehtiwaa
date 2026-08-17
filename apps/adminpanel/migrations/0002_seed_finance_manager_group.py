from django.db import migrations

# Finance Manager gets view+change on exactly these three payments models —
# nothing else. In particular, no bookings.Booking permission at all, which
# is what actually keeps session notes out of their reach (see
# apps.bookings.admin.BookingAdmin for the field-level backstop on top of
# this page-level restriction).
FINANCE_MANAGER_MODELS = [
    ("payments", "order"),
    ("payments", "payment"),
    ("payments", "invoice"),
]
FINANCE_MANAGER_ACTIONS = ["view", "change"]


def create_finance_manager_group(apps, schema_editor):
    # Permission rows for a model are normally created by Django's
    # post_migrate signal, which only fires once *all* migrations in this
    # run have applied — on a fresh install that's *after* this data
    # migration runs, so the payments.* permissions this migration needs
    # wouldn't exist yet. Creating them explicitly here makes this
    # migration correct regardless of ordering.
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    create_permissions(global_apps.get_app_config("payments"), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    group, _created = Group.objects.get_or_create(name="Finance Manager")

    permissions = []
    for app_label, model in FINANCE_MANAGER_MODELS:
        content_type = ContentType.objects.filter(app_label=app_label, model=model).first()
        if not content_type:
            continue
        for action in FINANCE_MANAGER_ACTIONS:
            permission = Permission.objects.filter(
                content_type=content_type, codename=f"{action}_{model}"
            ).first()
            if permission:
                permissions.append(permission)

    group.permissions.set(permissions)


def remove_finance_manager_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Finance Manager").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0001_initial"),
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_finance_manager_group, remove_finance_manager_group),
    ]
