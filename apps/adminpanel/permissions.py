"""Single source of truth for what a panel "role" (a Django Group) can
grant. Both the Roles editor (apps.adminpanel.forms.RoleForm) and every
panel view's `required_perms` derive from this list, so the UI that lets
staff build a role and the code that enforces it can never drift apart.

Deliberately section-level, not raw view/add/change/delete checkboxes —
toggling a capability grants the full CRUD bundle for that section in one
step, matching how WordPress/Ghost/Contentful-style admin panels present
permissions to non-technical staff.
"""

PANEL_CAPABILITIES = [
    {
        "key": "specialists",
        "label": "الأخصائيون",
        "perms": [
            "specialists.view_specialist",
            "specialists.add_specialist",
            "specialists.change_specialist",
            "specialists.delete_specialist",
        ],
    },
    {
        "key": "courses",
        "label": "الدورات",
        "perms": [
            "courses.view_course",
            "courses.add_course",
            "courses.change_course",
            "courses.delete_course",
        ],
    },
    {
        "key": "courses_own_only",
        "label": "الدورات: تقييد كل مقدّم بدوراته فقط",
        "perms": ["courses.manage_own_courses_only"],
    },
    {
        "key": "articles",
        "label": "المقالات",
        "perms": [
            "content.view_article",
            "content.add_article",
            "content.change_article",
            "content.delete_article",
            "content.view_category",
            "content.add_category",
            "content.change_category",
            "content.delete_category",
        ],
    },
    {
        "key": "articles_publish",
        "label": "نشر المقالات مباشرة (بدون مراجعة)",
        "perms": ["content.publish_article"],
    },
    {
        "key": "videos",
        "label": "الفيديوهات",
        "perms": [
            "content.view_video",
            "content.add_video",
            "content.change_video",
            "content.delete_video",
        ],
    },
    {
        "key": "homepage",
        "label": "الصفحة الرئيسية (الهيرو، البانرات، الشهادات)",
        "perms": [
            "core.view_homepagecontent",
            "core.change_homepagecontent",
            "content.view_banner",
            "content.add_banner",
            "content.change_banner",
            "content.delete_banner",
            "content.view_testimonial",
            "content.add_testimonial",
            "content.change_testimonial",
            "content.delete_testimonial",
        ],
    },
    {
        "key": "users",
        "label": "المستخدمون",
        "perms": ["accounts.view_user"],
    },
    {
        "key": "bookings",
        "label": "الحجوزات",
        "perms": ["bookings.view_booking"],
    },
    {
        "key": "payments",
        "label": "المدفوعات",
        "perms": [
            "payments.view_order",
            "payments.change_order",
            "payments.view_payment",
            "payments.change_payment",
            "payments.view_invoice",
            "payments.change_invoice",
        ],
    },
    {
        "key": "reports",
        "label": "التقارير",
        "perms": [
            "adminpanel.view_report",
            "adminpanel.add_report",
        ],
    },
]


def all_capability_perm_codenames():
    """Every permission codename across all capabilities, flattened —
    used to seed a full-access role (e.g. the default "مشرف" group)."""
    codenames = []
    for capability in PANEL_CAPABILITIES:
        codenames.extend(capability["perms"])
    return codenames


def admin_eligible_users():
    """Candidate pool for role assignment — every ordinary customer
    (accounts.User.role == "client") is excluded, regardless of is_staff,
    so a role-assignment picker never lists the platform's regular client
    base. Still includes anyone already staff (even if their `role` field
    was never updated) and every specialist/admin-role account, since
    those are exactly who ends up getting panel roles in practice."""
    from django.db.models import Q

    from apps.accounts.models import User

    return User.objects.filter(Q(is_staff=True) | ~Q(role="client")).distinct().order_by("email")
