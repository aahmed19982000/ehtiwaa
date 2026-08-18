from unittest.mock import MagicMock

from django.test import TestCase
from kombu.exceptions import OperationalError

from .tasks import safe_delay


class SafeDelayTests(TestCase):
    """Verified for real: Celery's task.delay() raises
    kombu.exceptions.OperationalError synchronously, at the call site, when
    the broker is unreachable — nothing in the codebase caught that before
    safe_delay existed, so a Redis outage would 500 every view that queues
    a notification (booking created/cancelled, ticket submitted, etc.)."""

    def test_broker_error_is_swallowed_not_raised(self):
        task = MagicMock()
        task.delay.side_effect = OperationalError("Connection refused")

        safe_delay(task, 1, key="value")  # must not raise

        task.delay.assert_called_once_with(1, key="value")

    def test_successful_delay_still_calls_through(self):
        task = MagicMock()

        safe_delay(task, 42)

        task.delay.assert_called_once_with(42)

    def test_non_broker_exceptions_still_propagate(self):
        task = MagicMock()
        task.delay.side_effect = ValueError("something else entirely")

        with self.assertRaises(ValueError):
            safe_delay(task, 1)
