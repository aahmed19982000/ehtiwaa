from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView

from apps.core.tasks import safe_delay
from apps.notifications.tasks import notify_booking_cancelled_task, notify_booking_created_task
from apps.payments.services import create_order_for_item
from apps.specialists.models import Specialist

from . import google_calendar
from .forms import BookingForm
from .models import Booking
from .services import (
    SLOT_LOOKAHEAD_DAYS,
    get_session_duration_minutes,
    get_session_price,
    get_slots_for_date,
)


class BookingCreateView(LoginRequiredMixin, View):
    template_name = "bookings/book.html"

    def get_specialist(self):
        return get_object_or_404(Specialist, pk=self.kwargs["specialist_pk"], status="approved")

    def get_selected_date(self, request):
        raw = request.GET.get("date") or request.POST.get("date")
        if raw:
            try:
                return date.fromisoformat(raw)
            except ValueError:
                pass
        return timezone.localdate()

    def build_context(self, specialist, selected_date, slots, form):
        return {
            "specialist": specialist,
            "selected_date": selected_date,
            "date_options": [
                timezone.localdate() + timedelta(days=i) for i in range(SLOT_LOOKAHEAD_DAYS)
            ],
            "slots": slots,
            "form": form,
        }

    def get(self, request, specialist_pk):
        specialist = self.get_specialist()
        selected_date = self.get_selected_date(request)
        duration = get_session_duration_minutes(specialist)
        slots = get_slots_for_date(specialist, selected_date, duration)
        form = BookingForm(
            initial={"date": selected_date, "contact_phone": request.user.phone or ""},
            available_slots=slots,
        )
        return render(
            request, self.template_name, self.build_context(specialist, selected_date, slots, form)
        )

    def post(self, request, specialist_pk):
        specialist = self.get_specialist()
        selected_date = self.get_selected_date(request)
        duration = get_session_duration_minutes(specialist)
        slots = get_slots_for_date(specialist, selected_date, duration)
        form = BookingForm(request.POST, available_slots=slots)

        if form.is_valid():
            naive_start = datetime.strptime(  # noqa: DTZ007 — localized on the next line
                form.cleaned_data["time_slot"], "%Y-%m-%dT%H:%M"
            )
            start = timezone.make_aware(naive_start)
            end = start + timedelta(minutes=duration)
            # Re-check right before creating, inside a transaction that
            # locks the specialist row — two concurrent requests for the
            # same specialist now serialize on that lock instead of both
            # passing .exists() before either has committed (the previous
            # plain check-then-create was a TOCTOU race that could produce
            # two overlapping bookings for the same slot).
            with transaction.atomic():
                Specialist.objects.select_for_update().get(pk=specialist.pk)
                already_taken = Booking.objects.filter(
                    specialist=specialist,
                    status__in=["pending", "confirmed"],
                    scheduled_start__lt=end,
                    scheduled_end__gt=start,
                ).exists()
                if not already_taken:
                    booking = Booking.objects.create(
                        client=request.user,
                        specialist=specialist,
                        status="pending",
                        scheduled_start=start,
                        scheduled_end=end,
                        contact_phone=form.cleaned_data["contact_phone"],
                        notes=form.cleaned_data["notes"],
                    )
            if already_taken:
                form.add_error(None, _("للأسف تم حجز هذا الموعد للتو، برجاء اختيار موعد آخر."))
            else:
                # No calendar event yet — that's created once payment is
                # confirmed (apps.bookings.services.confirm_bookings_from_paid_order),
                # so unpaid/abandoned bookings never clutter the specialist's
                # calendar with a session that may never happen.
                safe_delay(notify_booking_created_task, booking.pk)
                order = create_order_for_item(request.user, booking, get_session_price(specialist))
                messages.success(request, _("تم إرسال طلب الحجز — أكمل الدفع لتأكيد موعدك."))
                return redirect("payments:checkout", order_id=order.pk)

        slots = get_slots_for_date(specialist, selected_date, duration)
        return render(
            request, self.template_name, self.build_context(specialist, selected_date, slots, form)
        )


class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = "bookings/detail.html"
    context_object_name = "booking"

    def get_queryset(self):
        return Booking.objects.filter(client=self.request.user).select_related("specialist")


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = "bookings/list.html"
    context_object_name = "bookings"
    paginate_by = 10

    def get_queryset(self):
        return Booking.objects.filter(client=self.request.user).select_related("specialist")


class BookingCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, client=request.user)
        if booking.can_be_cancelled():
            booking.status = "cancelled"
            booking.cancelled_at = timezone.now()
            booking.cancelled_by = request.user
            booking.cancellation_reason = request.POST.get("reason", "")
            booking.save(
                update_fields=["status", "cancelled_at", "cancelled_by", "cancellation_reason"]
            )
            if booking.calendar_event_id:
                google_calendar.delete_event(booking.calendar_event_id)
            safe_delay(notify_booking_cancelled_task, booking.pk)
            messages.success(request, _("تم إلغاء الحجز."))
        else:
            messages.error(request, _("لا يمكن إلغاء هذا الحجز."))
        return redirect("bookings:list")
