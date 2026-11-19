from __future__ import annotations

from typing import TYPE_CHECKING

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone

from bats_ai.core.errors import FailureCode, ProcessingTaskError
from bats_ai.core.models import ProcessingTask

if TYPE_CHECKING:
    from django.db.models import QuerySet


def fail_processing_tasks(tasks: QuerySet[ProcessingTask], *, error: str, code: FailureCode) -> int:
    """Mark any of `tasks` still QUEUED/RUNNING as ERROR, recording why.

    Tasks already in a terminal state are left alone, so this never overwrites a
    COMPLETE (or an earlier, more specific ERROR). `error` is exposed through the
    API, so must be safe to show users. Returns the number of tasks marked.
    """
    return tasks.filter(
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING]
    ).update(
        status=ProcessingTask.Status.ERROR,
        error=error,
        output_metadata={"failureCode": code.value},
        modified=timezone.now(),
    )


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
            message, code = str(exc), exc.code
        elif isinstance(exc, SoftTimeLimitExceeded):
            message = f"Processing exceeded its time limit of {self.soft_time_limit} seconds"
            code = FailureCode.TIME_LIMIT
        else:
            message, code = f"Unexpected error ({type(exc).__name__})", FailureCode.UNEXPECTED
        fail_processing_tasks(
            ProcessingTask.objects.filter(celery_id=task_id), error=message, code=code
        )
