from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock
import uuid

from django.utils import timezone
import pytest

from bats_ai.core.models import ProcessingTask, ProcessingTaskType
from bats_ai.core.models.nabat import (
    NABatRecording,
    NABatRecordingList,
    NABatRecordingListItem,
)
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


@pytest.mark.django_db
def test_queue_item_retries_recording_whose_last_task_failed(mocker):
    item = _materialized_item()
    _processing_task(ProcessingTask.Status.ERROR)
    delay = mocker.patch.object(
        nabat_file_list.nabat_recording_initialize, "delay", return_value=MagicMock(id="new-task")
    )

    task_id = nabat_file_list._queue_item(item, "fake-token")

    assert task_id == "new-task"
    delay.assert_called_once_with(RECORDING_ID, SURVEY_EVENT_ID, "fake-token")
    assert ProcessingTask.objects.get(celery_id="new-task").status == ProcessingTask.Status.QUEUED


@pytest.mark.django_db
def test_queue_item_skips_recording_whose_last_task_completed(mocker):
    item = _materialized_item()
    _processing_task(ProcessingTask.Status.COMPLETE)
    delay = mocker.patch.object(nabat_file_list.nabat_recording_initialize, "delay")

    task_id = nabat_file_list._queue_item(item, "fake-token")

    assert task_id is None
    delay.assert_not_called()


@pytest.mark.django_db
def test_queue_item_redispatches_stale_running_task(mocker):
    item = _materialized_item()
    stale_task = _processing_task(ProcessingTask.Status.RUNNING)
    # .update() rather than .save(), which would reset `modified` to now.
    ProcessingTask.objects.filter(pk=stale_task.pk).update(
        modified=timezone.now() - timedelta(hours=1)
    )
    mocker.patch.object(
        nabat_file_list.nabat_recording_initialize, "delay", return_value=MagicMock(id="new-task")
    )

    task_id = nabat_file_list._queue_item(item, "fake-token")

    assert task_id == "new-task"
    stale_task.refresh_from_db()
    assert stale_task.status == ProcessingTask.Status.ERROR
