from __future__ import annotations

from datetime import timedelta
import sys
from unittest.mock import MagicMock
import uuid

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone
import pytest

from bats_ai.core.errors import (
    NABatAuthError,
    NABatGraphQLError,
    NABatMissingDataError,
    SpectrogramGenerationError,
)
from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Species
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation
from bats_ai.core.tasks.nabat import nabat_data_retrieval
from bats_ai.core.tasks.nabat import tasks as nabat_tasks
from bats_ai.core.tasks.nabat.nabat_data_retrieval import (
    STALE_TASK_ERROR,
    expire_stale_nabat_processing_tasks,
    is_nabat_recording_processed,
    nabat_recording_initialize,
)

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


def _response_body(
    *, presigned_url="https://example.com/recording.wav", errors=None, file_batches=None
) -> dict:
    batches = (
        [{"id": 1, "acousticFileBatchesByBatchId": {"nodes": file_batches}}]
        if file_batches is not None
        else []
    )
    body: dict = {
        "data": {
            "presignedUrlFromAcousticFile": (
                {"s3PresignedUrl": presigned_url} if presigned_url else None
            ),
            "surveyEventById": {
                "eventGeometryByEventGeometryId": None,
                "acousticBatchesBySurveyEventId": {"nodes": batches},
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
def test_annotations_skip_unvetted_and_unknown_species(mocker):
    processing_task = _queued_task()
    # Species rows are seeded by a data migration (with explicit pks, so creating new
    # ones collides with the sequence) - use one of those.
    species = Species.objects.order_by("pk").first()
    assert species is not None
    unknown_species_id = Species.objects.order_by("-pk").values_list("pk", flat=True)[0] + 1000
    _mock_nabat_response(
        mocker,
        body=_response_body(
            file_batches=[
                # Unvetted in NABat: no manual ID and no vetter.
                {"autoId": 1, "manualId": None, "vetter": None},
                # Vetted with a species that isn't in the local Species table.
                {"autoId": 1, "manualId": unknown_species_id, "vetter": "a@example.com"},
                {"autoId": 1, "manualId": species.pk, "vetter": "b@example.com"},
            ]
        ),
    )
    # Spectrogram generation is out of scope here.
    mocker.patch.object(nabat_data_retrieval, "generate_spectrograms")

    result = _run(processing_task)

    assert result.successful()
    recording = NABatRecording.objects.get(recording_id=RECORDING_ID)
    annotation = NABatRecordingAnnotation.objects.get(nabat_recording=recording)
    assert annotation.user_email == "b@example.com"
    assert list(annotation.species.all()) == [species]


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


def _complete_task(task, nabat_recording, presigned_url, processing_task):
    """Stand-in for generate_spectrograms that just marks the task COMPLETE, as it does."""
    processing_task.status = ProcessingTask.Status.COMPLETE
    processing_task.save()


@pytest.mark.django_db
def test_retry_after_spectrogram_failure_reuses_recording(mocker):
    species = Species.objects.order_by("pk").first()
    assert species is not None
    _mock_nabat_response(
        mocker,
        body=_response_body(
            file_batches=[{"autoId": 1, "manualId": species.pk, "vetter": "a@example.com"}]
        ),
    )

    # First attempt imports the metadata, then fails generating spectrograms.
    first_task = _queued_task()
    mocker.patch.object(
        nabat_data_retrieval,
        "generate_spectrograms",
        side_effect=SpectrogramGenerationError("Spectrogram generation failed: ValueError"),
    )
    _run(first_task)

    assert first_task.status == ProcessingTask.Status.ERROR
    recording = NABatRecording.objects.get(recording_id=RECORDING_ID)
    assert not is_nabat_recording_processed(RECORDING_ID)

    # Second attempt reuses that recording instead of failing on its unique recording_id.
    second_task = _queued_task()
    generate_spectrograms = mocker.patch.object(
        nabat_data_retrieval, "generate_spectrograms", side_effect=_complete_task
    )
    result = _run(second_task)

    assert result.successful()
    assert second_task.status == ProcessingTask.Status.COMPLETE
    assert generate_spectrograms.call_args.args[1] == recording
    assert NABatRecording.objects.count() == 1
    assert NABatRecordingAnnotation.objects.filter(nabat_recording=recording).count() == 1
    assert is_nabat_recording_processed(RECORDING_ID)


@pytest.mark.django_db
def test_metadata_import_is_atomic(mocker):
    species = Species.objects.order_by("pk").first()
    assert species is not None
    processing_task = _queued_task()
    _mock_nabat_response(
        mocker,
        body=_response_body(
            file_batches=[{"autoId": 1, "manualId": species.pk, "vetter": "a@example.com"}]
        ),
    )
    mocker.patch.object(
        nabat_data_retrieval.NABatRecordingAnnotation.objects,
        "create",
        side_effect=RuntimeError("annotation import failed"),
    )

    _run(processing_task)

    assert processing_task.status == ProcessingTask.Status.ERROR
    # The recording was created before the failure, but rolled back with it.
    assert not NABatRecording.objects.exists()


@pytest.mark.parametrize(
    ("has_recording", "task_statuses", "expected"),
    [
        (False, [], False),
        (False, [ProcessingTask.Status.COMPLETE], False),
        (True, [], True),
        (True, [ProcessingTask.Status.COMPLETE], True),
        (True, [ProcessingTask.Status.ERROR], False),
        (True, [ProcessingTask.Status.RUNNING], False),
        (True, [ProcessingTask.Status.COMPLETE, ProcessingTask.Status.ERROR], False),
        (True, [ProcessingTask.Status.ERROR, ProcessingTask.Status.COMPLETE], True),
    ],
)
@pytest.mark.django_db
def test_is_nabat_recording_processed(has_recording, task_statuses, expected):
    if has_recording:
        NABatRecording.objects.create(
            recording_id=RECORDING_ID, survey_event_id=SURVEY_EVENT_ID, name="recording.wav"
        )
    # Created oldest first, so the last status is the most recent task's.
    for status in task_statuses:
        processing_task = _queued_task()
        processing_task.status = status
        processing_task.save()

    assert is_nabat_recording_processed(RECORDING_ID) is expected


def _task_with_status(status, *, recording_id=RECORDING_ID, age=timedelta(0)) -> ProcessingTask:
    processing_task = ProcessingTask.objects.create(
        status=status,
        metadata={
            "type": ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
            "recordingId": recording_id,
        },
        celery_id=str(uuid.uuid4()),
    )
    # .update() rather than .save(), which would reset `modified` to now.
    ProcessingTask.objects.filter(pk=processing_task.pk).update(modified=timezone.now() - age)
    return processing_task


def test_time_limits_follow_setting():
    soft_limit = settings.BATAI_NABAT_TASK_TIME_LIMIT
    assert nabat_recording_initialize.soft_time_limit == soft_limit
    assert nabat_recording_initialize.time_limit == soft_limit + 30


@pytest.mark.django_db
def test_expire_stale_nabat_processing_tasks():
    stale = _task_with_status(ProcessingTask.Status.RUNNING, age=timedelta(hours=1))
    recent = _task_with_status(ProcessingTask.Status.RUNNING, age=timedelta(seconds=10))
    old_queued = _task_with_status(ProcessingTask.Status.QUEUED, age=timedelta(hours=1))
    other_recording = _task_with_status(
        ProcessingTask.Status.RUNNING, recording_id=RECORDING_ID + 1, age=timedelta(hours=1)
    )

    assert expire_stale_nabat_processing_tasks([RECORDING_ID]) == 1

    for processing_task in (stale, recent, old_queued, other_recording):
        processing_task.refresh_from_db()
    assert stale.status == ProcessingTask.Status.ERROR
    assert stale.error == STALE_TASK_ERROR
    assert recent.status == ProcessingTask.Status.RUNNING
    assert old_queued.status == ProcessingTask.Status.QUEUED
    assert other_recording.status == ProcessingTask.Status.RUNNING


@pytest.mark.django_db
def test_soft_time_limit_is_reported(mocker):
    processing_task = _queued_task()
    _mock_nabat_response(mocker, body=_response_body())
    download = MagicMock()
    download.iter_content.return_value = [b"audio"]
    mocker.patch.object(nabat_tasks.requests, "get", return_value=download)
    # generate_spectrograms imports this lazily, and the real module needs BatBot,
    # which the test environment doesn't install.
    batbot_metadata = MagicMock()
    batbot_metadata.generate_spectrogram_assets.side_effect = SoftTimeLimitExceeded()
    mocker.patch.dict(sys.modules, {"bats_ai.core.utils.batbot_metadata": batbot_metadata})

    result = _run(processing_task)

    assert isinstance(result.result, SoftTimeLimitExceeded)
    assert processing_task.status == ProcessingTask.Status.ERROR
    assert processing_task.error == (
        f"Processing exceeded its time limit of {settings.BATAI_NABAT_TASK_TIME_LIMIT} seconds"
    )
