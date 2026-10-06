from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from ninja import Form, Router, Schema

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

    print(payload.iss)
    print(payload.code)

    redirect_url = _reconstruct_file_list_redirect_url(payload.fileListId)
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.BATAI_NABAT_OIDC_CLIENT_ID,
        "client_secret": settings.BATAI_NABAT_OIDC_CLIENT_SECRET,
        "redirect_uri": redirect_url,
        "code": payload.code,
    }

    print(data)

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


def _start_first_unmaterialized_item(
    recording_list: NABatRecordingList, api_token: str
) -> str | None:
    # No explicit order_by: falls back to the model's default ordering
    # ("-recording_time", "id"), so "first" here matches however the list is sorted
    # for display.
    item = recording_list.items.filter(nabat_recording__isnull=True).first()
    if item is None:
        return None

    existing_task = ProcessingTask.objects.filter(
        metadata__recordingId=item.recording_id,
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()
    if existing_task:
        return existing_task.celery_id

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

    task_id = _start_first_unmaterialized_item(recording_list, api_token)
    return {"fileListId": recording_list.pk, "taskId": task_id}
