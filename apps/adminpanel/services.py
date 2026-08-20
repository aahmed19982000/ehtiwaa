import csv
import io

from deep_translator import GoogleTranslator
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.core.tasks import safe_delay
from apps.payments.models import Payment
from apps.specialists.models import ApprovalRequest, Specialist
from apps.specialists.tasks import notify_specialist_decision_task

from .models import Report


def approve_specialist(specialist, reviewer, notes=""):
    specialist.status = "approved"
    specialist.save(update_fields=["status"])
    ApprovalRequest.objects.create(
        specialist=specialist,
        reviewed_by=reviewer,
        decision="approved",
        notes=notes,
        decided_at=timezone.now(),
    )
    safe_delay(notify_specialist_decision_task, specialist.pk, "approved")


def reject_specialist(specialist, reviewer, notes=""):
    specialist.status = "rejected"
    specialist.save(update_fields=["status"])
    ApprovalRequest.objects.create(
        specialist=specialist,
        reviewed_by=reviewer,
        decision="rejected",
        notes=notes,
        decided_at=timezone.now(),
    )
    safe_delay(notify_specialist_decision_task, specialist.pk, "rejected", notes)


def generate_report(report_type, date_from, date_to, generated_by):
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    if report_type == "payments":
        writer.writerow(["البريد الإلكتروني", "المبلغ", "الحالة", "تاريخ الدفع"])
        payments = Payment.objects.select_related("order__user").filter(
            paid_at__date__gte=date_from, paid_at__date__lte=date_to
        )
        for payment in payments:
            writer.writerow(
                [payment.order.user.email, payment.order.total, payment.status, payment.paid_at]
            )
    elif report_type == "bookings":
        writer.writerow(["العميل", "الأخصائي", "الحالة", "موعد الجلسة"])
        bookings = Booking.objects.select_related("client", "specialist").filter(
            scheduled_start__date__gte=date_from, scheduled_start__date__lte=date_to
        )
        for booking in bookings:
            specialist_name = booking.specialist.full_name_ar or booking.specialist.full_name_en
            writer.writerow([booking.client.email, specialist_name, booking.status, booking.scheduled_start])
    elif report_type == "users":
        writer.writerow(["البريد الإلكتروني", "الدور", "تاريخ التسجيل"])
        users = User.objects.filter(date_joined__date__gte=date_from, date_joined__date__lte=date_to)
        for user in users:
            writer.writerow([user.email, user.role, user.date_joined])

    report = Report(report_type=report_type, date_from=date_from, date_to=date_to, generated_by=generated_by)
    # utf-8-sig so Excel opens the Arabic headers/values correctly instead
    # of mojibake — plain utf-8 has no BOM and Excel falls back to
    # Windows-1252 when reading CSVs without one.
    filename = f"{report_type}_{date_from}_{date_to}.csv"
    report.file.save(filename, ContentFile(buffer.getvalue().encode("utf-8-sig")), save=False)
    report.save()
    return report


def generate_unique_slug(model, text, slug_field="slug", fallback="item"):
    # Deliberately NOT allow_unicode=True — Course/Article detail pages are
    # routed with Django's plain <slug:slug> converter (ASCII-only), so a
    # Unicode slug would 404/NoReverseMatch on the public site. Arabic-only
    # titles slugify to "" (nothing ASCII to keep), hence the `fallback`.
    base_slug = slugify(text) or fallback
    slug = base_slug
    suffix = 2
    while model.objects.filter(**{slug_field: slug}).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def create_specialist_account(email, specialist_data):
    """Creates the linked User + Specialist together for a panel-added
    specialist. The random password is never shown to staff — it only
    exists so the account has a *usable* password, which Django's password
    reset form requires (an unusable password is silently excluded from
    reset emails). Staff should tell the specialist to use "نسيت كلمة
    المرور" with this email to set their own password."""

    # M2M can't be passed to Model.objects.create() — the row has to exist
    # first, then .set() links it.
    specialties = specialist_data.pop("specialties", None)

    user = User.objects.create(email=email, username=email, is_staff=False)
    user.set_password(get_random_string(32))
    user.save()
    specialist = Specialist.objects.create(user=user, **specialist_data)
    if specialties is not None:
        specialist.specialties.set(specialties)
    return specialist


def translate_article_fields(title, body, meta_title, meta_description):
    """Best-effort Arabic→English machine translation for the article
    editor's "English content" fields. Uses deep-translator's free,
    keyless GoogleTranslator wrapper (no API account) — per-field failures
    (network issue, or Google's ~5000-char length cap on `body`) are
    reported back rather than raised, so one failing field doesn't block
    the others; staff review and fix the results before saving either way."""

    translator = GoogleTranslator(source="ar", target="en")

    def safe_translate(text):
        text = (text or "").strip()
        if not text:
            return "", True
        try:
            return translator.translate(text) or "", True
        except Exception:
            return "", False

    fields = {
        "title": title,
        "body": body,
        "meta_title": meta_title,
        "meta_description": meta_description,
    }
    translated = {}
    failed_fields = []
    for name, text in fields.items():
        value, ok = safe_translate(text)
        translated[f"{name}_en"] = value
        if not ok:
            failed_fields.append(name)

    translated["failed_fields"] = failed_fields
    return translated
