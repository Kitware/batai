from __future__ import annotations

import base64
import json
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from ninja import Form, Schema
from ninja.pagination import RouterPaginated
from oauth2_provider.models import AccessToken
import requests

from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Species
from bats_ai.core.models.nabat import (
    NABatCompressedSpectrogram,
    NABatRecording,
    NABatRecordingAnnotation,
)
from bats_ai.core.tasks.nabat.nabat_data_retrieval import nabat_recording_initialize
from bats_ai.core.views.species import SpeciesSchema

logger = logging.getLogger(__name__)
router = RouterPaginated()


def admin_auth(request):
    if request.user.is_anonymous:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if len(token) > 0:
            try:
                access_token = AccessToken.objects.get(token=token)
            except AccessToken.DoesNotExist:
                access_token = None
            if access_token and access_token.user and not access_token.user.is_anonymous:
                request.user = access_token.user
    return True


SOFTWARE_ID = 81
QUERY = """
query fetchAcousticAndSurveyEventInfo {
  presignedUrlFromAcousticFile(acousticFileId: "%(acoustic_file_id)s") {
    s3PresignedUrl
  }
}
"""

UPDATE_QUERY = """
mutation UpdateQuery{
updateAcousticFileVet (
    surveyEventId: %(survey_event_id)d
    acousticFileId: %(acoustic_file_id)d
    softwareId: %(software_id)d
    speciesId: %(species_id)d,
  ) {
    acousticFileBatchId
  }
}
"""


def decode_jwt(token):
    # Split the token into parts
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    # JWT uses base64url encoding, so need to fix padding
    payload = parts[1]
    padding = "=" * (4 - (len(payload) % 4))  # Fix padding if needed
    payload += padding

    # Decode the payload
    decoded_bytes = base64.urlsafe_b64decode(payload)
    decoded_str = decoded_bytes.decode("utf-8")

    # Parse JSON
    return json.loads(decoded_str)


def get_email_if_authorized(
    request: HttpRequest,
    api_token: str,
    recording_id: int | None = None,
    recording_pk: int | None = None,
) -> str | JsonResponse:
    """
    Check API token validity with NABat API and return email from JWT if authorized.

    If the user is a superuser, short-circuit and return their email.
    Either `recording_id` or `recording_pk` must be provided.

    `recording_pk` refers to the primary key of a NABatRecording, from which the actual
    `recording_id` is retrieved.
    """
    # Superuser shortcut
    if request.user and request.user.is_authenticated and request.user.is_superuser:
        return request.user.email or "superuser@nabat.org"
    # Decode JWT token
    try:
        payload = decode_jwt(api_token)
        email = payload.get("email")
        if not email:
            raise ValueError("Email not found in JWT payload")
    except Exception as e:
        logger.error(f"Failed to decode JWT: {e}")
        return JsonResponse({"error": "Invalid API token"}, status=400)

    # Resolve recording_id from recording_pk if needed
    if recording_id is None:
        if recording_pk is None:
            return JsonResponse(
                {"error": "Either recording_id or recording_pk must be provided"}, status=400
            )
        try:
            nabat_recording = NABatRecording.objects.get(pk=recording_pk)
            recording_id = nabat_recording.recording_id
        except NABatRecording.DoesNotExist:
            return JsonResponse(
                {"error": f"NABatRecording with id {recording_pk} does not exist"}, status=404
            )

    # Verify access with NABat API
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    query = QUERY % {"acoustic_file_id": recording_id}
    try:
        response = requests.post(
            settings.BATAI_NABAT_API_URL, json={"query": query}, headers=headers
        )
    except Exception as e:
        logger.error(f"API request error: {e}")
        return JsonResponse({"error": "Failed to connect to NABat API"}, status=500)

    if response.status_code != 200:
        logger.error(f"NABat API rejected access: {response.status_code} - {response.text}")
        return JsonResponse(
            {"error": "Failed to verify access with NABat API"}, status=response.status_code
        )

    try:
        data = response.json()
        if data["data"]["presignedUrlFromAcousticFile"] is None:
            return JsonResponse({"error": "Recording not found or access denied"}, status=403)
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.error(f"Error decoding NABat API response: {e}")
        return JsonResponse({"error": "Malformed response from NABat API"}, status=500)

    return email


class NABatRecordingSchema(Schema):
    name: str
    recording_id: int
    recorded_date: str | None
    equipment: str | None
    comments: str | None
    recording_location: str | None
    grts_cell_id: int | None
    grts_cell: int | None


class NABatRecordingGenerateSchema(Schema):
    apiToken: str
    recordingId: int
    surveyEventId: int


def update_nabat_species(species_id: int, api_token: str, recording_id: int, survey_event_id: int):
    """
    Update the species for a NABat recording using the NABat API.

    This function is called after creating or updating a recording annotation.
    """
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    batch_query = UPDATE_QUERY % {
        "survey_event_id": survey_event_id,
        "software_id": SOFTWARE_ID,
        "acoustic_file_id": recording_id,
        "species_id": species_id,
    }
    try:
        response = requests.post(
            settings.BATAI_NABAT_API_URL, json={"query": batch_query}, headers=headers
        )
        json_response = response.json()
        if json_response.get("errors"):
            logger.error(f"API Error: {json_response['errors']}")
            return JsonResponse(json_response, status=500)
    except Exception as e:
        logger.error(f"API Request Failed: {e}")
        return JsonResponse({"error": "Failed to connect to NABat API"}, status=500)
    return "NABat species updated successfully."


@router.post("/", auth=None)
def generate_nabat_recording(
    request: HttpRequest,
    payload: Form[NABatRecordingGenerateSchema],
):
    existing_task = ProcessingTask.objects.filter(
        metadata__recordingId=payload.recordingId,
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()

    if existing_task:
        return JsonResponse(
            {
                "error": "A task is already processing this recordingId.",
                "taskId": existing_task.celery_id,
                "status": existing_task.status,
            },
            status=409,
        )

    nabat_recording = NABatRecording.objects.filter(recording_id=payload.recordingId)
    if not nabat_recording.exists():
        # use a task to start downloading the file using the API key and generate the spectrograms
        task = nabat_recording_initialize.delay(
            payload.recordingId, payload.surveyEventId, payload.apiToken
        )
        with transaction.atomic():
            ProcessingTask.objects.create(
                name=f"Processing Recording {payload.recordingId}",
                status=ProcessingTask.Status.QUEUED,
                metadata={
                    "type": ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
                    "recordingId": payload.recordingId,
                },
                celery_id=task.id,
            )
        return {"taskId": task.id}
    # we want to check the apiToken and make sure the user has access to the file
    # before returning it
    api_token = payload.apiToken
    recording_id = payload.recordingId
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    batch_query = QUERY % {
        "acoustic_file_id": recording_id,
    }
    try:
        response = requests.post(
            settings.BATAI_NABAT_API_URL, json={"query": batch_query}, headers=headers
        )
        logger.info(response.json())
    except Exception:
        return JsonResponse(response.json(), status=500)

    if response.status_code == 200:
        try:
            batch_data = response.json()
            logger.info(batch_data)
            if batch_data["data"]["presignedUrlFromAcousticFile"] is None:
                return JsonResponse({"error": "Recording not found or access denied"}, status=404)
            else:
                return {"recordingId": nabat_recording.first().pk}
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.error(f"Error processing batch data: {e}")
            return JsonResponse({"error": f"Error with API Request: {e}"}, status=500)
    else:
        logger.error(f"Failed to fetch data: {response.status_code}, {response.text}")
        return JsonResponse(response.json(), status=500)


@router.get("/{id}/spectrogram", auth=admin_auth)
def get_spectrogram(request: HttpRequest, id: int):
    try:
        nabat_recording = NABatRecording.objects.get(pk=id)
    except NABatRecording.DoesNotExist:
        return {"error": "Recording not found"}

    spectrogram = nabat_recording.spectrogram

    compressed = nabat_recording.compressed_spectrogram

    spectro_data = {
        "urls": spectrogram.image_url_list,
        "spectroInfo": {
            "spectroId": spectrogram.pk,
            "width": spectrogram.width,
            "height": spectrogram.height,
            "start_time": 0,
            "end_time": spectrogram.duration,
            "low_freq": spectrogram.frequency_min,
            "high_freq": spectrogram.frequency_max,
        },
    }
    if compressed:
        spectro_data["compressed"] = {
            "start_times": compressed.starts,
            "end_times": compressed.stops,
        }

    # Serialize the annotations using AnnotationSchema
    annotations_data = []
    sequence_annotations_data = []

    spectro_data["annotations"] = annotations_data
    spectro_data["sequence"] = sequence_annotations_data
    return spectro_data


@router.get("/{id}/spectrogram/compressed", auth=admin_auth)
def get_spectrogram_compressed(request: HttpRequest, id: int, apiToken: str):
    try:
        nabat_recording = NABatRecording.objects.get(pk=id)
    except NABatRecording.DoesNotExist:
        return JsonResponse({"error": "Recording does not exist"}, status=404)

    email_or_response = get_email_if_authorized(request, apiToken, nabat_recording.recording_id)
    if isinstance(email_or_response, JsonResponse):
        return email_or_response

    compressed_spectrogram = NABatCompressedSpectrogram.objects.filter(nabat_recording=id).first()

    if not compressed_spectrogram:
        return JsonResponse({"error": "Compressed Spectrogram not found"}, status=404)

    spectro_data = {
        "urls": compressed_spectrogram.image_url_list,
        "mask_urls": compressed_spectrogram.mask_url_list,
        "spectroInfo": {
            "spectroId": compressed_spectrogram.pk,
            "width": compressed_spectrogram.spectrogram.width,
            "start_time": 0,
            "end_time": compressed_spectrogram.spectrogram.duration,
            "height": compressed_spectrogram.spectrogram.height,
            "low_freq": compressed_spectrogram.spectrogram.frequency_min,
            "high_freq": compressed_spectrogram.spectrogram.frequency_max,
            "start_times": compressed_spectrogram.starts,
            "end_times": compressed_spectrogram.stops,
            "widths": compressed_spectrogram.widths,
            "compressedWidth": compressed_spectrogram.length,
        },
        "annotations": [],
        "sequence": [],
    }

    return spectro_data


class NABatRecordingAnnotationSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    owner: str | None = None
    confidence: float
    id: int | None = None
    hasDetails: bool

    @classmethod
    def from_orm(cls, obj: NABatRecordingAnnotation, **kwargs):
        return cls(
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
            owner=obj.user_email,
            confidence=obj.confidence,
            comments=obj.comments,
            model=obj.model,
            id=obj.pk,
            hasDetails=obj.additional_data is not None,
        )


class NABatRecordingAnnotationDetailsSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    owner: str | None = None
    confidence: float
    id: int | None = None
    details: dict
    hasDetails: bool

    @classmethod
    def from_orm(cls, obj: NABatRecordingAnnotation, **kwargs):
        return cls(
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
            owner=obj.user_email,
            confidence=obj.confidence,
            comments=obj.comments,
            model=obj.model,
            hasDetails=obj.additional_data is not None,
            details=obj.additional_data,
            id=obj.pk,
        )


class NABatCreateRecordingAnnotationSchema(Schema):
    recordingId: int
    species: list[int]
    comments: str = None
    model: str = None
    confidence: float
    apiToken: str


@router.get("/{nabat_recording_id}/recording-annotations", auth=admin_auth)
def get_nabat_recording_annotation(
    request: HttpRequest,
    nabat_recording_id: int,
    apiToken: str | None = None,
):
    email_or_response = get_email_if_authorized(request, apiToken, recording_pk=nabat_recording_id)
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use

    fileAnnotations = NABatRecordingAnnotation.objects.filter(nabat_recording=nabat_recording_id)

    if request.user.is_authenticated and request.user.is_superuser:
        # If the user is a superuser, return all annotations
        pass
    elif user_email:
        fileAnnotations = fileAnnotations.filter(
            Q(user_email=user_email) | Q(user_email__isnull=True)
        )

    fileAnnotations = fileAnnotations.order_by("confidence")

    output = [
        NABatRecordingAnnotationSchema.from_orm(fileAnnotation).dict()
        for fileAnnotation in fileAnnotations
    ]
    return output


@router.get("recording-annotation/{id}", auth=admin_auth, response=NABatRecordingAnnotationSchema)
def get_recording_annotation(request: HttpRequest, id: int, apiToken: str):
    email_or_response = get_email_if_authorized(request, apiToken, recording_pk=id)
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use
    try:
        annotation = NABatRecordingAnnotation.objects.get(pk=id)

        if user_email:
            annotation = annotation.filter(Q(user_email=user_email) | Q(user_email__isnull=True))

        return NABatRecordingAnnotationSchema.from_orm(annotation).dict()
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({"error": "Recording annotation not found."}, 404)


@router.get(
    "recording-annotation/{id}/details",
    auth=admin_auth,
    response=NABatRecordingAnnotationDetailsSchema,
)
def get_recording_annotation_details(request: HttpRequest, id: int, apiToken: str):
    email_or_response = get_email_if_authorized(request, apiToken, recording_pk=id)
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use
    try:
        annotation = NABatRecordingAnnotation.objects.get(
            Q(pk=id) & (Q(user_email=user_email) | Q(user_email__isnull=True))
        )

        return NABatRecordingAnnotationDetailsSchema.from_orm(annotation).dict()
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({"error": "Recording annotation not found."}, 404)


@router.put("recording-annotation", auth=None, response={200: str})
def create_recording_annotation(request: HttpRequest, data: NABatCreateRecordingAnnotationSchema):
    email_or_response = get_email_if_authorized(
        request, data.apiToken, recording_pk=data.recordingId
    )
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use

    token_data = decode_jwt(data.apiToken)
    user_id = token_data["sub"]

    try:
        recording = NABatRecording.objects.get(pk=data.recordingId)

        # Create the recording annotation
        annotation = NABatRecordingAnnotation.objects.create(
            nabat_recording=recording,
            user_email=user_email,
            user_id=user_id,
            comments=data.comments,
            model=data.model,
            confidence=data.confidence,
        )

        # Add species
        for species_id in data.species:
            species = Species.objects.get(pk=species_id)
            annotation.species.add(species)
        return "Recording annotation created successfully."
    except NABatRecording.DoesNotExist:
        return JsonResponse({"error": "Recording not found."}, 404)
    except Species.DoesNotExist:
        return JsonResponse({"error": "One or more species IDs not found."}, 404)


@router.patch("recording-annotation/{id}", auth=None, response={200: str})
def update_recording_annotation(
    request: HttpRequest, id: int, data: NABatCreateRecordingAnnotationSchema
):
    """Update an existing recording annotation but doesn't update NABat.

    It requires the user to be authenticated
    and authorized to modify the specific recording. The user must provide an API token, which is
    validated to ensure the user has access to the recording. The user can update comments, model,
    confidence, and species associated with the annotation. If the species list is provided,
    it clears the existing species and adds the new ones. The endpoint returns a
    success message or an error message if the recording or species are not found.
    """
    email_or_response = get_email_if_authorized(
        request, data.apiToken, recording_pk=data.recordingId
    )
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use
    try:
        annotation = NABatRecordingAnnotation.objects.get(pk=id, user_email=user_email)
        # Check permission

        # Update fields if provided
        if data.comments is not None:
            annotation.comments = data.comments
        if data.model is not None:
            annotation.model = data.model
        if data.confidence is not None:
            annotation.confidence = data.confidence
        if data.species is not None:
            annotation.species.clear()  # Clear existing species
            for species_id in data.species:
                species = Species.objects.get(pk=species_id)
                annotation.species.add(species)

        annotation.save()
        return "Recording annotation updated successfully."
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({"error": "Recording not found."}, 404)
    except Species.DoesNotExist:
        return JsonResponse({"error": "One or more species IDs not found."}, 404)


@router.patch("recording-annotation/{id}/push-to-nabat", auth=None, response={200: str})
def update_nabat_recording_annotation(
    request: HttpRequest, id: int, data: NABatCreateRecordingAnnotationSchema
):
    """Update an existing recording annotation in NABat."""
    email_or_response = get_email_if_authorized(
        request, data.apiToken, recording_pk=data.recordingId
    )
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use

    try:
        annotation = NABatRecordingAnnotation.objects.get(pk=id, user_email=user_email)
        # Check permission

        # Update fields if provided
        if data.comments is not None:
            annotation.comments = data.comments
        if data.model is not None:
            annotation.model = data.model
        if data.confidence is not None:
            annotation.confidence = data.confidence
        if data.species is not None:
            if len(data.species) == 1:
                species_id = data.species[0]
                return update_nabat_species(
                    species_id,
                    data.apiToken,
                    annotation.nabat_recording.recording_id,
                    annotation.nabat_recording.survey_event_id,
                )
            elif len(data.species) > 1:
                return JsonResponse(
                    {"error": "NABat only supports one species per recording annotation."},
                    status=400,
                )
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({"error": "Recording not found."}, 404)
    except Species.DoesNotExist:
        return JsonResponse({"error": "One or more species IDs not found."}, 404)


# TODO: Determine if this will be implemented for NABat
@router.delete("recording-annotation/{id}", auth=None, response={200: str})
def delete_recording_annotation(request: HttpRequest, id: int, apiToken: str, recordingId: str):
    email_or_response = get_email_if_authorized(request, apiToken, recording_pk=recordingId)
    if isinstance(email_or_response, JsonResponse):
        return email_or_response
    user_email = email_or_response  # safe to use
    try:
        annotation = NABatRecordingAnnotation.objects.get(pk=id, user_email=user_email)

        # Check permission
        annotation.delete()
        return "Recording annotation deleted successfully."
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({"error": "Recording not found for this user."}, 404)
