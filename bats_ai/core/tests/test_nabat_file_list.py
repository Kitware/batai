from __future__ import annotations

from datetime import timedelta
import uuid

from django.conf import settings
from django.utils import timezone
import pytest

from bats_ai.core.models import ProcessingTask, ProcessingTaskType
from bats_ai.core.models.nabat import (
    NABatRecording,
    NABatRecordingList,
    NABatRecordingListItem,
)
from bats_ai.core.tasks.nabat import nabat_data_retrieval
from bats_ai.core.views.nabat import nabat_file_list

RECORDING_ID = 12345
SURVEY_EVENT_ID = 678


def _materialized_item() -> NABatRecordingListItem:
    """Create a list item whose NABatRecording already exists (from an earlier task)."""
    recording = NABatRecording.objects.create(
        recording_id=RECORDING_ID, survey_event_id=SURVEY_EVENT_ID, name="recording.wav"
    )
    recording_list = NABatRecordingList.objects.create(nabat_file_list_id=1)
    return NABatRecordingListItem.objects.create(
        recording_list=recording_list,
        recording_id=RECORDING_ID,
        survey_event_id=SURVEY_EVENT_ID,
        nabat_recording=recording,
    )


def _processing_task(status: ProcessingTask.Status) -> ProcessingTask:
    return ProcessingTask.objects.create(
        status=status,
        metadata={
            "type": ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
            "recordingId": RECORDING_ID,
        },
        celery_id=str(uuid.uuid4()),
    )


def _mock_apply_async(mocker):
    return mocker.patch.object(nabat_data_retrieval.nabat_recording_initialize, "apply_async")


@pytest.mark.django_db
def test_queue_item_retries_recording_whose_last_task_failed(
    mocker, django_capture_on_commit_callbacks
):
    item = _materialized_item()
    _processing_task(ProcessingTask.Status.ERROR)
    apply_async = _mock_apply_async(mocker)

    with django_capture_on_commit_callbacks(execute=True):
        task_id = nabat_file_list._queue_item(item, "fake-token")

    apply_async.assert_called_once_with(
        args=(RECORDING_ID, SURVEY_EVENT_ID, "fake-token"),
        task_id=task_id,
        expires=settings.BATAI_NABAT_TASK_QUEUE_TIMEOUT,
    )
    assert ProcessingTask.objects.get(celery_id=task_id).status == ProcessingTask.Status.QUEUED


@pytest.mark.django_db
def test_queue_item_skips_recording_whose_last_task_completed(
    mocker, django_capture_on_commit_callbacks
):
    item = _materialized_item()
    _processing_task(ProcessingTask.Status.COMPLETE)
    apply_async = _mock_apply_async(mocker)

    with django_capture_on_commit_callbacks(execute=True):
        task_id = nabat_file_list._queue_item(item, "fake-token")

    assert task_id is None
    apply_async.assert_not_called()


@pytest.mark.django_db
def test_queue_item_redispatches_stale_running_task(mocker, django_capture_on_commit_callbacks):
    item = _materialized_item()
    stale_task = _processing_task(ProcessingTask.Status.RUNNING)
    # .update() rather than .save(), which would reset `modified` to now.
    ProcessingTask.objects.filter(pk=stale_task.pk).update(
        modified=timezone.now() - timedelta(hours=1)
    )
    apply_async = _mock_apply_async(mocker)

    with django_capture_on_commit_callbacks(execute=True):
        task_id = nabat_file_list._queue_item(item, "fake-token")

    assert task_id != stale_task.celery_id
    apply_async.assert_called_once()
    stale_task.refresh_from_db()
    assert stale_task.status == ProcessingTask.Status.ERROR


@pytest.mark.django_db
def test_queue_item_redispatches_expired_queued_task(mocker, django_capture_on_commit_callbacks):
    item = _materialized_item()
    expired_task = _processing_task(ProcessingTask.Status.QUEUED)
    ProcessingTask.objects.filter(pk=expired_task.pk).update(
        created=timezone.now() - timedelta(hours=3)
    )
    apply_async = _mock_apply_async(mocker)

    with django_capture_on_commit_callbacks(execute=True):
        task_id = nabat_file_list._queue_item(item, "fake-token")

    assert task_id != expired_task.celery_id
    apply_async.assert_called_once()
    expired_task.refresh_from_db()
    assert expired_task.status == ProcessingTask.Status.ERROR
