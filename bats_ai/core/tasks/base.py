from __future__ import annotations

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from bats_ai.core.errors import ProcessingTaskError
from bats_ai.core.models import ProcessingTask


class ProcessingTaskBase(Task):
    """Celery task base that marks the task's ProcessingTask as ERROR on failure.

    Without this, any exception the task body doesn't explicitly handle leaves its
    ProcessingTask at QUEUED/RUNNING forever, which callers treat as still in flight.

    Only fires when the task raises; a worker killed outright (OOM, SIGKILL) never
    reaches it. Also doesn't fire when the task function is called directly rather
    than through Celery (`.delay()`, `.apply()`, or eager mode).
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # ProcessingTask.error is exposed through the API, so only store messages
        # from our own error classes; anything else gets just its type, with the
        # details left to logs and Sentry.
        if isinstance(exc, ProcessingTaskError):
            message = str(exc)
        elif isinstance(exc, SoftTimeLimitExceeded):
            message = f"Processing exceeded its time limit of {self.soft_time_limit} seconds"
        else:
            message = f"Unexpected error ({type(exc).__name__})"
        # The status filter keeps this from touching a task that already reached a
        # terminal state.
        ProcessingTask.objects.filter(
            celery_id=task_id,
            status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
        ).update(status=ProcessingTask.Status.ERROR, error=message)
