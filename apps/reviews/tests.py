from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.specialists.models import Specialist

from .models import Review
from .services import submit_review

User = get_user_model()


def _make_specialist(username):
    user = User.objects.create_user(
        username=username, email=f"{username}@example.com", password="whatever-123"
    )
    return Specialist.objects.create(
        user=user, status="approved", full_name_ar=f"د. {username}", hourly_rate=100
    )


class SubmitReviewServiceTests(TestCase):
    """apps.reviews.models.Review enforces `unique_together = ("user",
    "content_type", "object_id")` at the DB level, and submit_review() uses
    update_or_create on exactly those fields — confirming this project does
    deliberately allow only one review per user per item (a resubmission
    revises it in place), not an assumption."""

    def setUp(self):
        self.reviewer = User.objects.create_user(
            username="reviewer1", email="reviewer1@example.com", password="whatever-123"
        )
        self.specialist = _make_specialist("target1")

    def test_second_submission_updates_existing_review_not_duplicate(self):
        submit_review(self.reviewer, self.specialist, 3, "معقول")
        submit_review(self.reviewer, self.specialist, 5, "ممتاز فعلاً")

        reviews = Review.objects.filter(user=self.reviewer, object_id=self.specialist.pk)
        self.assertEqual(reviews.count(), 1)
        self.assertEqual(reviews.first().rating, 5)
        self.assertEqual(reviews.first().comment, "ممتاز فعلاً")

    def test_different_users_each_get_their_own_review(self):
        other_reviewer = User.objects.create_user(
            username="reviewer2", email="reviewer2@example.com", password="whatever-123"
        )
        submit_review(self.reviewer, self.specialist, 4)
        submit_review(other_reviewer, self.specialist, 2)

        self.assertEqual(Review.objects.filter(object_id=self.specialist.pk).count(), 2)

    def test_duplicate_row_at_db_level_is_rejected(self):
        submit_review(self.reviewer, self.specialist, 4)
        from django.contrib.contenttypes.models import ContentType
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            Review.objects.create(
                user=self.reviewer,
                content_type=ContentType.objects.get_for_model(self.specialist),
                object_id=self.specialist.pk,
                rating=1,
            )


class ReviewSignalTests(TestCase):
    def setUp(self):
        self.specialist = _make_specialist("ratedspecialist")

    def test_average_rating_and_count_update_on_add(self):
        reviewer1 = User.objects.create_user(
            username="r1", email="r1@example.com", password="whatever-123"
        )
        reviewer2 = User.objects.create_user(
            username="r2", email="r2@example.com", password="whatever-123"
        )

        submit_review(reviewer1, self.specialist, 4)
        self.specialist.refresh_from_db()
        self.assertEqual(self.specialist.reviews_count, 1)
        self.assertEqual(self.specialist.average_rating, Decimal("4.00"))

        submit_review(reviewer2, self.specialist, 2)
        self.specialist.refresh_from_db()
        self.assertEqual(self.specialist.reviews_count, 2)
        self.assertEqual(self.specialist.average_rating, Decimal("3.00"))

    def test_average_rating_and_count_update_on_delete(self):
        reviewer1 = User.objects.create_user(
            username="r3", email="r3@example.com", password="whatever-123"
        )
        reviewer2 = User.objects.create_user(
            username="r4", email="r4@example.com", password="whatever-123"
        )
        review1 = submit_review(reviewer1, self.specialist, 4)
        submit_review(reviewer2, self.specialist, 2)

        review1.delete()

        self.specialist.refresh_from_db()
        self.assertEqual(self.specialist.reviews_count, 1)
        self.assertEqual(self.specialist.average_rating, Decimal("2.00"))

    def test_deleting_all_reviews_resets_to_zero(self):
        reviewer = User.objects.create_user(
            username="r5", email="r5@example.com", password="whatever-123"
        )
        review = submit_review(reviewer, self.specialist, 5)
        review.delete()

        self.specialist.refresh_from_db()
        self.assertEqual(self.specialist.reviews_count, 0)
        self.assertEqual(self.specialist.average_rating, 0)


class SpecialistReviewCreateViewTests(TestCase):
    def setUp(self):
        self.specialist = _make_specialist("viewspecialist")
        self.url = reverse("reviews:specialist-review", kwargs={"pk": self.specialist.pk})
        self.user = User.objects.create_user(
            username="vieweruser", email="vieweruser@example.com", password="whatever-123"
        )

    def test_anonymous_user_cannot_submit_review(self):
        response = self.client.post(self.url, data={"rating": 5, "comment": "great"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertEqual(Review.objects.count(), 0)

    def test_authenticated_user_can_submit_and_resubmit(self):
        self.client.force_login(self.user)
        self.client.post(self.url, data={"rating": 3, "comment": "ok"})
        self.client.post(self.url, data={"rating": 5, "comment": "great actually"})

        self.assertEqual(Review.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Review.objects.get(user=self.user).rating, 5)
