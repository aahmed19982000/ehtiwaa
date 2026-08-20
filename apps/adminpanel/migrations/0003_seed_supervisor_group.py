from django.db import migrations

# Full-access "مشرف" (Supervisor) role — every capability the panel's
# Roles editor knows about (apps.adminpanel.permissions.PANEL_CAPABILITIES),
# flattened. Kept inline (not imported) so this migration stays a frozen,
# self-contained snapshot the way apps.adminpanel's Finance Manager seed
# migration (0002) already is — if PANEL_CAPABILITIES grows later, that's a
# separate migration, not a change to this one's behavior on replay.
SUPERVISOR_PERMISSIONS = [
    ("specialists", "view_specialist"),
    ("specialists", "add_specialist"),
    ("specialists", "change_specialist"),
    ("specialists", "delete_specialist"),
    ("courses", "view_course"),
    ("courses", "add_course"),
    ("courses", "change_course"),
    ("courses", "delete_course"),
    ("content", "view_article"),
    ("content", "add_article"),
    ("content", "change_article"),
    ("content", "delete_article"),
    ("content", "view_category"),
    ("content", "add_category"),
    ("content", "change_category"),
    ("content", "delete_category"),
    ("content", "publish_article"),
    ("content", "view_video"),
    ("content", "add_video"),
    ("content", "change_video"),
    ("content", "delete_video"),
    ("core", "view_homepagecontent"),
    ("core", "change_homepagecontent"),
    ("content", "view_banner"),
    ("content", "add_banner"),
    ("content", "change_banner"),
    ("content", "delete_banner"),
    ("content", "view_testimonial"),
    ("content", "add_testimonial"),
    ("content", "change_testimonial"),
    ("content", "delete_testimonial"),
    ("accounts", "view_user"),
    ("bookings", "view_booking"),
    ("payments", "view_order"),
    ("payments", "change_order"),
    ("payments", "view_payment"),
    ("payments", "change_payment"),
    ("payments", "view_invoice"),
    ("payments", "change_invoice"),
    ("adminpanel", "view_report"),
    ("adminpanel", "add_report"),
]

SEEDED_APPS = [
    "specialists",
    "courses",
    "content",
    "core",
    "accounts",
    "bookings",
    "payments",
    "adminpanel",
]


def seed_supervisor_group(apps, schema_editor):
    # Same ordering hazard 0002 documents: on a fresh install this data
    # migration can run before post_migrate has created permission rows
    # for models touched earlier in the same run, so create them explicitly.
    from django.apps import apps as global_apps
    from django.contrib.auth.management import create_permissions

    for app_label in SEEDED_APPS:
        create_permissions(global_apps.get_app_config(app_label), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _created = Group.objects.get_or_create(name="مشرف")

    permissions = []
    for app_label, codename in SUPERVISOR_PERMISSIONS:
        permission = Permission.objects.filter(
            content_type__app_label=app_label, codename=codename
        ).first()
        if permission:
            permissions.append(permission)

    group.permissions.set(permissions)


def remove_supervisor_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="مشرف").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0002_seed_finance_manager_group"),
        ("specialists", "0009_specialist_can_write_articles"),
        ("courses", "0004_alter_course_options"),
        ("content", "0009_alter_article_options_article_created_by_and_more"),
        ("core", "0004_seed_homepage_content"),
        ("accounts", "0003_alter_profile_avatar"),
        ("bookings", "0003_booking_calendar_event_id_booking_meeting_link"),
        ("payments", "0002_alter_payment_options_payment_failure_reason_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_supervisor_group, remove_supervisor_group),
    ]
