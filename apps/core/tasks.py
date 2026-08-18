import logging

from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)


def safe_delay(task, *args, **kwargs):
    """Queues a Celery task without letting a broker outage (Redis down —
    verified for real: task.delay() raises kombu.exceptions.OperationalError
    synchronously, right at the call site, when the broker is unreachable)
    crash the calling request. Every notification task in this project is
    fire-and-forget from a primary action (booking created, order paid,
    ticket submitted) that must still succeed even if the notification
    couldn't be queued."""
    try:
        task.delay(*args, **kwargs)
    except OperationalError:
        logger.exception("Failed to queue Celery task %s — broker unreachable", task.name)
