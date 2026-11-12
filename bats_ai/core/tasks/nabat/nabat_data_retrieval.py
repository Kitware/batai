from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
import requests

from bats_ai.celery import app
from bats_ai.core.errors import (
    NABatAuthError,
    NABatGraphQLError,
    NABatInvalidResponseError,
    NABatMissingDataError,
    NABatRequestError,
)
from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Species
from bats_ai.core.models.nabat import (
    NABatRecording,
    NABatRecordingAnnotation,
    NABatRecordingListItem,
)
from bats_ai.core.tasks.base import ProcessingTaskBase

from .tasks import generate_spectrograms

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NABatDataRetrieval")

SOFTWARE_ID = 81
QUERY = """
query fetchAcousticAndSurveyEventInfo {
  presignedUrlFromAcousticFile(acousticFileId: "%(acoustic_file_id)s") {
    s3PresignedUrl
  }
  surveyEventById(id: "%(survey_event_id)d") {
    createdBy
    createdDate
    eventGeometryByEventGeometryId {
      description
      geom {
        geojson
      }
    }
    acousticBatchesBySurveyEventId(filter: {softwareId: {equalTo:%(software_id)d}}) {
      nodes {
        id
        acousticFileBatchesByBatchId(filter: {fileId: {equalTo: "%(acoustic_file_id)s"}}) {
          nodes {
            autoId
            manualId
            vetter
            speciesByManualId {
              speciesCode
            }
          }
        }
      }
    }
  }
  acousticFileById(id: "%(acoustic_file_id)d") {
    fileName
    recordingTime
    s3Verified
    sizeBytes
  }
}
"""


def get_or_create_processing_task(recording_id, request_id):
    """
    Fetch or create a ProcessingTask with the given metadata and status filters.

    Uses `get` with try-except block to handle object retrieval.

    Args:
        recording_id (int): The recording ID for the task metadata.
        request_id (str): The Celery request ID to store in the task.

    Returns:
        tuple: A tuple with the ProcessingTask instance and a boolean indicating if it was created.
    """
    # Define the metadata filter with specific keys in the JSON metadata field
    metadata_filter = {
        "type": ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
        "recordingId": recording_id,
    }

    # Try to get an existing task or handle the case where it's not found
    try:
        # Attempt to get a task based on the metadata filter and status
        processing_task = ProcessingTask.objects.get(
            Q(metadata__contains=metadata_filter)
            & Q(status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING])
            & Q(celery_id=request_id)
        )
        # If task is found, return the task with False (not created)
        return processing_task, False

    except ObjectDoesNotExist:
        # If task does not exist, create a new one with the given defaults
        with transaction.atomic():
            processing_task = ProcessingTask.objects.create(
                metadata=metadata_filter,
                status=ProcessingTask.Status.QUEUED,  # Default status if creating a new task
                celery_id=request_id,
            )
        # Return the newly created task and True (created)
        return processing_task, True

    except MultipleObjectsReturned:
        # If multiple tasks are found, raise an exception (shouldn't happen if data is correct)
        raise


def _require(data: dict, *path: str):
    """Walk `path` into NABat response `data`, raising if any step is null or absent."""
    node: Any = data
    for i, key in enumerate(path):
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            raise NABatMissingDataError(
                f"NABat returned no {'.'.join(path[: i + 1])} "
                "(it may not exist, or this user may not have access to it)"
            )
    return node


def _fetch_recording_data(batch_query: str, api_token: str) -> dict:
    """POST the recording query to NABat and return the parsed, error-free response."""
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    try:
        response = requests.post(
            settings.BATAI_NABAT_API_URL,
            json={"query": batch_query},
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as e:
        raise NABatRequestError(f"Could not reach the NABat API: {type(e).__name__}") from e

    if response.status_code in (401, 403):
        logger.error("NABat rejected credentials: %s - %s", response.status_code, response.text)
        raise NABatAuthError(
            f"NABat rejected this user's credentials (HTTP {response.status_code})"
        )
    if response.status_code != 200:
        logger.error("NABat request failed: %s - %s", response.status_code, response.text)
        raise NABatRequestError(f"NABat API request failed (HTTP {response.status_code})")

    try:
        batch_data = response.json()
    except json.JSONDecodeError as e:
        raise NABatInvalidResponseError("NABat API returned a response that isn't JSON") from e

    # GraphQL reports errors with HTTP 200, alongside null fields in `data`.
    if errors := batch_data.get("errors"):
        messages = "; ".join(str(error.get("message", error)) for error in errors)
        raise NABatGraphQLError(f"NABat API returned errors: {messages}")

    return batch_data


@app.task(bind=True, base=ProcessingTaskBase)
def nabat_recording_initialize(self, recording_id: int, survey_event_id: int, api_token: str):
    processing_task, _created = get_or_create_processing_task(recording_id, self.request.id)

    processing_task.status = ProcessingTask.Status.RUNNING
    processing_task.save()
    batch_query = QUERY % {
        "acoustic_file_id": recording_id,
        "survey_event_id": survey_event_id,
        "software_id": SOFTWARE_ID,
    }
    self.update_state(
        state="Progress",
        meta={"description": "Fetching NAbat Recording Data"},
    )
    batch_data = _fetch_recording_data(batch_query, api_token)

    self.update_state(
        state="Progress",
        meta={"description": "Fetching Recording File"},
    )

    presigned_url = _require(batch_data, "data", "presignedUrlFromAcousticFile", "s3PresignedUrl")
    logger.info("Presigned URL obtained. Downloading file...")

    logger.info("Creating NA Bat Recording...")
    nabat_recording = create_nabat_recording_from_response(
        batch_data, recording_id, survey_event_id
    )
    generate_spectrograms(self, nabat_recording, presigned_url, processing_task)


def create_nabat_recording_from_response(response_data, recording_id, survey_event_id):
    survey_event = _require(response_data, "data", "surveyEventById")
    file_name = _require(response_data, "data", "acousticFileById", "fileName")

    # Optional fields
    recording_location_data = (
        (survey_event.get("eventGeometryByEventGeometryId") or {}).get("geom") or {}
    ).get("geojson")

    # Create geometry for the recording location if available
    if recording_location_data:
        coordinates = recording_location_data.get("coordinates", [])
        recording_location = (
            Point(coordinates[0], coordinates[1]) if len(coordinates) == 2 else None
        )
    else:
        recording_location = None

    # Create the NABatRecording instance
    nabat_recording = NABatRecording.objects.create(
        recording_id=recording_id,
        survey_event_id=survey_event_id,
        name=file_name,
        recording_location=recording_location,
    )

    # nabat_recording_initialize is dispatched with just a bare recording_id, with no
    # awareness of which NABatRecordingListItem(s), if any, triggered it - so backfill
    # any that were waiting on this recording_id becoming available. Without this, those
    # items would stay permanently unmaterialized and get retried on every future
    # create/advance call, eventually crashing on recording_id's uniqueness constraint.
    NABatRecordingListItem.objects.filter(
        recording_id=recording_id, nabat_recording__isnull=True
    ).update(nabat_recording=nabat_recording)

    acoustic_batches_nodes = survey_event["acousticBatchesBySurveyEventId"]["nodes"]
    if len(acoustic_batches_nodes) > 0:
        batch_data = acoustic_batches_nodes[0]["acousticFileBatchesByBatchId"]["nodes"]
        for node in batch_data:
            species_id = node.get("manualId", False)
            if species_id is not False:
                annotation = NABatRecordingAnnotation.objects.create(
                    nabat_recording=nabat_recording,
                    user_email=node["vetter"],
                )
                species = Species.objects.get(pk=species_id)
                annotation.species.add(species)

    return nabat_recording
