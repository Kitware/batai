from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
import json
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from ninja import Form, Router, Schema
import requests

from bats_ai.core.models import ProcessingTask, ProcessingTaskType
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingList, NABatRecordingListItem
from bats_ai.core.tasks.nabat.nabat_data_retrieval import nabat_recording_initialize
from bats_ai.core.views.nabat.nabat_recording import get_auth_header

logger = logging.getLogger(__name__)
router = Router()

# Trimmed to what NABatRecordingList/NABatRecordingListItem actually cache (see
# bats_ai/core/models/nabat/nabat_recording_list.py): name/projectId/createdBy at the
# list level, and id/surveyEventId/fileName/recordingTime per file. surveyEventId is
# what makes nabat_recording_initialize (the existing per-recording fetch+materialize
# task) callable for a list item later, since that task has no other way to learn it
# for a file that's never been individually opened before.
#
# acousticFileByFileId is the schema's real per-node accessor (confirmed via NABat's
# own query editor) - not `file`, which is what an earlier CSV-export sample response
# used for the same relation.
QUERY = """
query acousticFileList {
  acousticFileListById(id: %(file_list_id)d) {
    name
    projectId
    createdBy
    acousticFileAcousticFileListsByListId {
      totalCount
      nodes {
        acousticFileByFileId {
          id
          surveyEventId
          fileName
          recordingTime
        }
      }
    }
  }
}
"""


class NABatFileListAuthorizationSchema(Schema):
    fileListId: int
    iss: str
    code: str


def _reconstruct_file_list_redirect_url(file_list_id):
    url_root = settings.BATAI_WEB_URL.rstrip("/")
    return f"{url_root}/nabat/file-list/auth/?fileListId={file_list_id}"


# Parallel to nabat_recording.authorize_nabat_requests, duplicated rather than shared
# since the two differ only in how the redirect_uri is reconstructed (fileListId vs.
# recordingId/surveyEventId) - that has to match exactly what NABat signed the auth
# code against, so it's tied to the specific frontend route for each flow.
@router.post("/authorize", auth=None)
def authorize_nabat_file_list_requests(
    request: HttpRequest, payload: Form[NABatFileListAuthorizationSchema]
):
    if payload.iss != settings.BATAI_NABAT_OIDC_ISSUER:
        return JsonResponse({"error": "Unexpected issuer"}, status=400)

    redirect_url = _reconstruct_file_list_redirect_url(payload.fileListId)
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.BATAI_NABAT_OIDC_CLIENT_ID,
        "client_secret": settings.BATAI_NABAT_OIDC_CLIENT_SECRET,
        "redirect_uri": redirect_url,
        "code": payload.code,
    }

    try:
        response = requests.post(
            f"{settings.BATAI_NABAT_OIDC_BASE_URL}/protocol/openid-connect/token",
            data=data,
            timeout=30,
        )
        response_json = response.json()
        if response.status_code != 200:
            logger.error(
                "Keycloak token exchange rejected: %s - %s", response.status_code, response.text
            )
            return JsonResponse(
                {"error": "Keycloak token exchange failed."}, status=response.status_code
            )
        return JsonResponse(response_json, status=200)
    except Exception:
        logger.exception("Keycloak token exchange failed")
        return JsonResponse({"error": "Keycloak token exchange failed"}, status=500)


class NABatFileListCreateSchema(Schema):
    fileListId: int


def _parse_recording_time(value: str | None) -> datetime | None:
    if not value:
        return None
    # NABat sends a naive timestamp with no UTC offset or `Z`. TIME_ZONE is UTC in this
    # project, so treat the value as already UTC rather than leaving it naive (USE_TZ=True
    # would otherwise emit a RuntimeWarning and assume UTC anyway) - unconfirmed whether
    # NABat's own clock is actually UTC rather than local-to-the-deployment-site, but this
    # is only a display/sort field, so getting it wrong doesn't affect correctness elsewhere.
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _create_file_list(file_list_id: int, file_list_data: dict) -> NABatRecordingList:
    nodes = file_list_data["acousticFileAcousticFileListsByListId"]["nodes"]

    with transaction.atomic():
        recording_list = NABatRecordingList.objects.create(
            nabat_file_list_id=file_list_id,
            name=file_list_data.get("name"),
            nabat_project_id=file_list_data.get("projectId"),
            created_by_email=file_list_data.get("createdBy"),
        )
        for node in nodes:
            file_data = node["acousticFileByFileId"]
            NABatRecordingListItem.objects.create(
                recording_list=recording_list,
                recording_id=file_data["id"],
                survey_event_id=file_data["surveyEventId"],
                file_name=file_data.get("fileName"),
                recording_time=_parse_recording_time(file_data.get("recordingTime")),
                nabat_recording=NABatRecording.objects.filter(recording_id=file_data["id"]).first(),
            )
    return recording_list


def _queue_item(item: NABatRecordingListItem, api_token: str) -> str | None:
    """Ensure `item` is being materialized.

    Dispatches nabat_recording_initialize unless it's already materialized or
    already has a task in flight. Returns the in-flight task's celery id (whether
    just dispatched or already running), or None if already materialized.

    No live check against NABat happens here - just a present-looking token gets
    passed through. An invalid/expired token is still caught, just inside the task
    itself when it calls NABat, surfacing as a "failed" status rather than an
    immediate error from this call. A previously-failed item (no ProcessingTask
    still QUEUED/RUNNING, nothing materialized) gets retried automatically here,
    which is intentional.

    Checks for an in-flight task before checking nabat_recording_id: that FK gets
    backfilled by create_nabat_recording_from_response partway through
    nabat_recording_initialize, well before the task actually finishes generating
    spectrograms - callers need the still-running task's id to wait on, not None,
    even once the row exists (see _item_status, which has the same ordering for
    the same reason).
    """
    existing_task = ProcessingTask.objects.filter(
        metadata__recordingId=item.recording_id,
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()
    if existing_task:
        return existing_task.celery_id

    if item.nabat_recording_id is not None:
        return None

    task = nabat_recording_initialize.delay(item.recording_id, item.survey_event_id, api_token)
    with transaction.atomic():
        ProcessingTask.objects.create(
            name=f"Processing Recording {item.recording_id}",
            status=ProcessingTask.Status.QUEUED,
            metadata={
                "type": ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
                "recordingId": item.recording_id,
            },
            celery_id=task.id,
        )
    return task.id


def _queue_positions(
    recording_list: NABatRecordingList, position: int, api_token: str
) -> dict[int, str]:
    """Queue `position` and its next two neighbors (0-indexed, in the list's own default order).

    Shared by create() (always position 0, so the first item a user would open is
    already in flight by the time the list loads) and the queue-ahead endpoint
    (whatever position the frontend is currently viewing). Silently skips any of
    the three positions that falls past the end of the list.
    """
    items = list(recording_list.items.all())
    queued_task_ids = {}
    for target_position in (position, position + 1, position + 2):
        if not 0 <= target_position < len(items):
            continue
        task_id = _queue_item(items[target_position], api_token)
        if task_id is not None:
            queued_task_ids[target_position] = task_id
    return queued_task_ids


@router.post("/create", auth=None)
def create_nabat_file_list(
    request: HttpRequest,
    payload: Form[NABatFileListCreateSchema],
):
    api_token = get_auth_header(request)
    if not api_token:
        return JsonResponse({"error": "Missing or invalid Authorization header"}, status=401)

    # Always re-run against NABat, even if the list already exists locally - this
    # doubles as the access re-check for the "already exists" branch, since it's cheap
    # enough to just rerun rather than add a second skinny query for that alone.
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    query = QUERY % {"file_list_id": payload.fileListId}
    try:
        response = requests.post(
            settings.BATAI_NABAT_API_URL, json={"query": query}, headers=headers, timeout=30
        )
    except Exception:
        logger.exception("API request error")
        return JsonResponse({"error": "Failed to connect to NABat API"}, status=500)

    if response.status_code != 200:
        logger.error("NABat API rejected access: %s - %s", response.status_code, response.text)
        return JsonResponse(
            {"error": "Failed to verify access with NABat API"}, status=response.status_code
        )

    try:
        data = response.json()
        file_list_data = data["data"]["acousticFileListById"]
        if file_list_data is None:
            return JsonResponse({"error": "File list not found or access denied"}, status=404)
    except (KeyError, TypeError, json.JSONDecodeError):
        logger.exception("Error decoding NABat API response")
        return JsonResponse({"error": "Malformed response from NABat API"}, status=500)

    recording_list = NABatRecordingList.objects.filter(
        nabat_file_list_id=payload.fileListId
    ).first()
    if recording_list is None:
        try:
            recording_list = _create_file_list(payload.fileListId, file_list_data)
        except IntegrityError:
            # Lost a race with a concurrent create for the same file list.
            recording_list = get_object_or_404(
                NABatRecordingList, nabat_file_list_id=payload.fileListId
            )

    queued_task_ids = _queue_positions(recording_list, 0, api_token)
    return {"fileListId": recording_list.pk, "queuedTaskIds": queued_task_ids}


@router.post("/{file_list_id}/{position}", auth=None)
def queue_nabat_file_list_items(
    request: HttpRequest,
    file_list_id: int,
    position: int,
):
    """Ensure `position` and the two items after it are materialized or in flight.

    Called by the frontend when navigating to the `position`-th item (0-indexed,
    in the list's own default order) of an already-created list, to keep a couple
    of items ahead of wherever the user currently is queued up. Silently does
    nothing for any of the three positions that falls past the end of the list.
    """
    api_token = get_auth_header(request)
    if not api_token:
        return JsonResponse({"error": "Missing or invalid Authorization header"}, status=401)

    recording_list = get_object_or_404(NABatRecordingList, nabat_file_list_id=file_list_id)
    queued_task_ids = _queue_positions(recording_list, position, api_token)
    return {"fileListId": recording_list.pk, "queuedTaskIds": queued_task_ids}


class NABatFileListItemStatus(str, Enum):
    EXISTS = "exists"
    QUEUED = "queued"
    FAILED = "failed"
    DOES_NOT_EXIST = "does_not_exist"


class NABatFileListItemSchema(Schema):
    id: int
    recordingId: int
    fileName: str | None
    recordingTime: datetime | None
    status: NABatFileListItemStatus
    # The local NABatRecording pk, once materialized - null until then. This is
    # what the frontend actually needs to link to /nabat/{id}/spectrogram; the
    # NABat-side recordingId above isn't a valid route param on its own.
    nabatRecordingId: int | None


class NABatFileListStatusSchema(Schema):
    fileListId: int
    items: list[NABatFileListItemSchema]


def _item_status(item: NABatRecordingListItem, task_statuses: list[str]) -> NABatFileListItemStatus:
    # Checked before nabat_recording_id: that FK gets backfilled by
    # create_nabat_recording_from_response partway through nabat_recording_initialize,
    # well before the task actually finishes generating spectrograms - a still-running
    # task always means "not ready yet," even once the row exists.
    in_flight = (ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING)
    if any(s in in_flight for s in task_statuses):
        return NABatFileListItemStatus.QUEUED
    if item.nabat_recording_id is not None:
        return NABatFileListItemStatus.EXISTS
    if ProcessingTask.Status.ERROR in task_statuses:
        return NABatFileListItemStatus.FAILED
    return NABatFileListItemStatus.DOES_NOT_EXIST


@router.get("/{file_list_id}", response=NABatFileListStatusSchema, auth=None)
def get_nabat_file_list(request: HttpRequest, file_list_id: int):
    """Per-item status for an already-created list: exists / queued / failed / does_not_exist.

    No NABat call happens here - a token just needs to be present, for consistency
    with every other endpoint on this router, even though nothing here actually
    uses it.
    """
    api_token = get_auth_header(request)
    if not api_token:
        return JsonResponse({"error": "Missing or invalid Authorization header"}, status=401)

    recording_list = get_object_or_404(NABatRecordingList, nabat_file_list_id=file_list_id)
    items = list(recording_list.items.all())

    task_statuses_by_recording_id: dict[int, list[str]] = {}
    tasks = ProcessingTask.objects.filter(
        metadata__type=ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
        metadata__recordingId__in=[item.recording_id for item in items],
    )
    for task in tasks:
        task_statuses_by_recording_id.setdefault(task.metadata["recordingId"], []).append(
            task.status
        )

    return {
        "fileListId": recording_list.pk,
        "items": [
            {
                "id": item.pk,
                "recordingId": item.recording_id,
                "fileName": item.file_name,
                "recordingTime": item.recording_time,
                "status": _item_status(
                    item, task_statuses_by_recording_id.get(item.recording_id, [])
                ),
                "nabatRecordingId": item.nabat_recording_id,
            }
            for item in items
        ],
    }
