from __future__ import annotations

from unittest.mock import MagicMock
import uuid

import pytest

from bats_ai.core.errors import NABatAuthError, NABatGraphQLError, NABatMissingDataError
from bats_ai.core.models import ProcessingTask, ProcessingTaskType
from bats_ai.core.models.nabat import NABatRecording
from bats_ai.core.tasks.nabat import nabat_data_retrieval
from bats_ai.core.tasks.nabat.nabat_data_retrieval import nabat_recording_initialize

RECORDING_ID = 12345
SURVEY_EVENT_ID = 678


def _queued_task() -> ProcessingTask:
    """Create the QUEUED row the views create when dispatching the task."""
    return ProcessingTask.objects.create(
        name=f"Processing Recording {RECORDING_ID}",
        status=ProcessingTask.Status.QUEUED,
        metadata={
            "type": ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
            "recordingId": RECORDING_ID,
        },
        celery_id=str(uuid.uuid4()),
    )


def _run(processing_task: ProcessingTask):
    # Must go through .apply() rather than calling the task directly, or Celery's
    # tracer (and so ProcessingTaskBase.on_failure) is skipped.
    result = nabat_recording_initialize.apply(
        args=(RECORDING_ID, SURVEY_EVENT_ID, "fake-token"),
        task_id=processing_task.celery_id,
    )
    processing_task.refresh_from_db()
    return result


def _mock_nabat_response(mocker, *, status_code=200, body=None) -> None:
    response = MagicMock(status_code=status_code, text="response body")
    response.json.return_value = body
    mocker.patch.object(nabat_data_retrieval.requests, "post", return_value=response)


def _response_body(*, presigned_url="https://example.com/recording.wav", errors=None) -> dict:
    body: dict = {
        "data": {
            "presignedUrlFromAcousticFile": (
                {"s3PresignedUrl": presigned_url} if presigned_url else None
            ),
            "surveyEventById": {
                "eventGeometryByEventGeometryId": None,
                "acousticBatchesBySurveyEventId": {"nodes": []},
            },
            "acousticFileById": {"fileName": "recording.wav"},
        }
    }
    if errors is not None:
        body["errors"] = errors
    return body


@pytest.mark.django_db
def test_graphql_errors_are_stored(mocker):
    processing_task = _queued_task()
    _mock_nabat_response(
        mocker,
        body=_response_body(
            presigned_url=None, errors=[{"message": "permission denied for acoustic_file"}]
        ),
    )

    result = _run(processing_task)

    assert result.failed()
    assert isinstance(result.result, NABatGraphQLError)
    assert processing_task.status == ProcessingTask.Status.ERROR
    assert "permission denied for acoustic_file" in processing_task.error
    assert not NABatRecording.objects.exists()


@pytest.mark.django_db
def test_null_field_without_graphql_errors(mocker):
    processing_task = _queued_task()
    _mock_nabat_response(mocker, body=_response_body(presigned_url=None))

    result = _run(processing_task)

    assert isinstance(result.result, NABatMissingDataError)
    assert processing_task.status == ProcessingTask.Status.ERROR
    assert "presignedUrlFromAcousticFile" in processing_task.error
    assert "may not have access" in processing_task.error
    assert not NABatRecording.objects.exists()


@pytest.mark.django_db
def test_rejected_credentials(mocker):
    processing_task = _queued_task()
    _mock_nabat_response(mocker, status_code=401)

    result = _run(processing_task)

    assert isinstance(result.result, NABatAuthError)
    assert processing_task.status == ProcessingTask.Status.ERROR
    assert processing_task.error == "NABat rejected this user's credentials (HTTP 401)"


@pytest.mark.django_db
def test_unexpected_error_stores_only_its_type(mocker):
    processing_task = _queued_task()
    _mock_nabat_response(mocker, body=_response_body())
    mocker.patch.object(
        nabat_data_retrieval,
        "create_nabat_recording_from_response",
        side_effect=RuntimeError("sensitive detail"),
    )

    result = _run(processing_task)

    assert isinstance(result.result, RuntimeError)
    assert processing_task.status == ProcessingTask.Status.ERROR
    assert processing_task.error == "Unexpected error (RuntimeError)"


@pytest.mark.django_db
def test_on_failure_leaves_terminal_tasks_alone():
    processing_task = _queued_task()
    processing_task.status = ProcessingTask.Status.COMPLETE
    processing_task.save()

    nabat_recording_initialize.on_failure(
        RuntimeError("late failure"), processing_task.celery_id, (), {}, None
    )

    processing_task.refresh_from_db()
    assert processing_task.status == ProcessingTask.Status.COMPLETE
    assert processing_task.error == ""
