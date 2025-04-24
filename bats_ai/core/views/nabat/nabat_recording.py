import base64
import json
import logging

from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from ninja import Form, Schema
from ninja.pagination import RouterPaginated
import requests

from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Species, colormap
from bats_ai.core.models.nabat import (
    NABatCompressedSpectrogram,
    NABatRecording,
    NABatRecordingAnnotation,
)
from bats_ai.core.views.species import SpeciesSchema
from bats_ai.tasks.nabat.nabat_data_retrieval import nabat_recording_initialize
from bats_ai.tasks.tasks import predict_compressed

logger = logging.getLogger(__name__)


router = RouterPaginated()
SOFTWARE_ID = 81
BASE_URL = 'https://api.sciencebase.gov/nabat-graphql/graphql'
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
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError('Invalid JWT token format')

    # JWT uses base64url encoding, so need to fix padding
    payload = parts[1]
    padding = '=' * (4 - (len(payload) % 4))  # Fix padding if needed
    payload += padding

    # Decode the payload
    decoded_bytes = base64.urlsafe_b64decode(payload)
    decoded_str = decoded_bytes.decode('utf-8')

    # Parse JSON
    return json.loads(decoded_str)


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


@router.post('/', auth=None)
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
                'error': 'A task is already processing this recordingId.',
                'taskId': existing_task.celery_id,
                'status': existing_task.status,
            },
            status=409,
        )

    nabat_recording = NABatRecording.objects.filter(recording_id=payload.recordingId)
    if not nabat_recording.exists():
        # use a task to start downloading the file using the API key and generate the spectrograms
        task = nabat_recording_initialize.delay(
            payload.recordingId, payload.surveyEventId, payload.apiToken
        )
        ProcessingTask.objects.create(
            name=f'Processing Recording {payload.recordingId}',
            status=ProcessingTask.Status.QUEUED,
            metadata={
                'type': ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
                'recordingId': payload.recordingId,
            },
            celery_id=task.id,
        )
        return {'taskId': task.id}
    # we want to check the apiToken and make sure the user has access to the file before returning it
    api_token = payload.apiToken
    recording_id = payload.recordingId
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    batch_query = QUERY % {
        'acoustic_file_id': recording_id,
    }
    try:
        response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
        logger.info(response.json())
    except Exception:
        return JsonResponse(response.json(), status=500)

    if response.status_code == 200:
        try:
            batch_data = response.json()
            logger.info(batch_data)
            if batch_data['data']['presignedUrlFromAcousticFile'] is None:
                return JsonResponse({'error': 'Recording not found or access denied'}, status=404)
            else:
                return {'recordingId': nabat_recording.first().pk}
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.error(f'Error processing batch data: {e}')
            return JsonResponse({'error': f'Error with API Request: {e}'}, status=500)
    else:
        logger.error(f'Failed to fetch data: {response.status_code}, {response.text}')
        return JsonResponse(response.json(), status=500)


@router.get('/', auth=None)
def get_nabat_recording_spectrogram(request: HttpRequest, id: int, apiToken: str):
    try:
        nabat_recording = NABatRecording.objects.get(pk=id)
    except NABatRecording.DoesNotExist:
        return JsonResponse({'error': 'Recording does not exist'}, status=404)

    headers = {'Authorization': f'Bearer {apiToken}', 'Content-Type': 'application/json'}
    batch_query = QUERY % {
        'acoustic_file_id': nabat_recording.recording_id,
    }
    try:
        response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
    except Exception as e:
        logger.error(f'API Request Failed: {e}')
        return JsonResponse({'error': 'Failed to connect to NABat API'}, status=500)

    if response.status_code != 200:
        logger.error(f'Failed NABat API Query: {response.status_code} - {response.text}')
        return JsonResponse({'error': 'Failed to verify recording access'}, status=500)

    try:
        batch_data = response.json()
        if batch_data['data']['presignedUrlFromAcousticFile'] is None:
            return JsonResponse({'error': 'Recording not found or access denied'}, status=404)
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.error(f'Error parsing NABat API response: {e}')
        return JsonResponse({'error': 'Invalid response from NABat API'}, status=500)

    with colormap(None):
        spectrogram = nabat_recording.spectrogram

    compressed = nabat_recording.compressed_spectrogram

    spectro_data = {
        'url': spectrogram.image_url,
        'spectroInfo': {
            'spectroId': spectrogram.pk,
            'width': spectrogram.width,
            'height': spectrogram.height,
            'start_time': 0,
            'end_time': spectrogram.duration,
            'low_freq': spectrogram.frequency_min,
            'high_freq': spectrogram.frequency_max,
        },
    }
    if compressed:
        spectro_data['compressed'] = {
            'start_times': compressed.starts,
            'end_times': compressed.stops,
        }

    spectro_data['annotations'] = []
    spectro_data['temporal'] = []
    return spectro_data


@router.post('/{id}/spectrogram/compressed/predict', auth=None)
def predict_spectrogram_compressed(request: HttpRequest, id: int):
    try:
        recording = NABatRecording.objects.get(pk=id)
        compressed_spectrogram = NABatCompressedSpectrogram.objects.filter(
            nabat_recording=id
        ).first()
    except compressed_spectrogram.DoesNotExist:
        return {'error': 'Compressed Spectrogram'}
    except recording.DoesNotExist:
        return {'error': 'Recording does not exist'}

    label, score, confs = predict_compressed(compressed_spectrogram.image_file)
    confidences = []
    confidences = [{'label': key, 'value': float(value)} for key, value in confs.items()]
    sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
    output = {
        'label': label,
        'score': float(score),
        'confidences': sorted_confidences,
    }
    return output


@router.get('/{id}/spectrogram', auth=None)
def get_spectrogram(request: HttpRequest, id: int):
    try:
        nabat_recording = NABatRecording.objects.get(pk=id)
    except NABatRecording.DoesNotExist:
        return {'error': 'Recording not found'}

    with colormap(None):
        spectrogram = nabat_recording.spectrogram

    compressed = nabat_recording.compressed_spectrogram

    spectro_data = {
        'url': spectrogram.image_url,
        'spectroInfo': {
            'spectroId': spectrogram.pk,
            'width': spectrogram.width,
            'height': spectrogram.height,
            'start_time': 0,
            'end_time': spectrogram.duration,
            'low_freq': spectrogram.frequency_min,
            'high_freq': spectrogram.frequency_max,
        },
    }
    if compressed:
        spectro_data['compressed'] = {
            'start_times': compressed.starts,
            'end_times': compressed.stops,
        }

    # Serialize the annotations using AnnotationSchema
    annotations_data = []
    temporal_annotations_data = []

    spectro_data['annotations'] = annotations_data
    spectro_data['temporal'] = temporal_annotations_data
    return spectro_data


@router.get('/{id}/spectrogram/compressed', auth=None)
def get_spectrogram_compressed(request: HttpRequest, id: int, apiToken: str):
    try:
        nabat_recording = NABatRecording.objects.get(pk=id)
    except NABatRecording.DoesNotExist:
        return JsonResponse({'error': 'Recording does not exist'}, status=404)

    headers = {'Authorization': f'Bearer {apiToken}', 'Content-Type': 'application/json'}
    batch_query = QUERY % {
        'acoustic_file_id': nabat_recording.recording_id,
    }

    try:
        response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
    except Exception as e:
        logger.error(f'API request failed: {e}')
        return JsonResponse({'error': 'Failed to verify API token'}, status=500)

    if response.status_code != 200:
        logger.error(f'Failed API auth check: {response.status_code} - {response.text}')
        return JsonResponse(response.json(), status=response.status_code)

    try:
        batch_data = response.json()
        if batch_data['data']['presignedUrlFromAcousticFile'] is None:
            return JsonResponse({'error': 'Recording not found or access denied'}, status=404)
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.error(f'Error processing batch data: {e}')
        return JsonResponse({'error': 'Error processing API response'}, status=500)

    # --- passed authorization check ---

    compressed_spectrogram = NABatCompressedSpectrogram.objects.filter(nabat_recording=id).first()

    if not compressed_spectrogram:
        return JsonResponse({'error': 'Compressed Spectrogram not found'}, status=404)

    spectro_data = {
        'url': compressed_spectrogram.image_url,
        'spectroInfo': {
            'spectroId': compressed_spectrogram.pk,
            'width': compressed_spectrogram.spectrogram.width,
            'start_time': 0,
            'end_time': compressed_spectrogram.spectrogram.duration,
            'height': compressed_spectrogram.spectrogram.height,
            'low_freq': compressed_spectrogram.spectrogram.frequency_min,
            'high_freq': compressed_spectrogram.spectrogram.frequency_max,
            'start_times': compressed_spectrogram.starts,
            'end_times': compressed_spectrogram.stops,
            'widths': compressed_spectrogram.widths,
            'compressedWidth': compressed_spectrogram.length,
        },
        'annotations': [],
        'temporal': [],
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


@router.get('/{nabat_recording_id}/recording-annotations', auth=None)
def get_nabat_recording_annotation(
    request: HttpRequest,
    nabat_recording_id: int,
    apiToken: str | None = None,
):
    token_data = decode_jwt(apiToken)
    user_email = token_data['email']

    fileAnnotations = NABatRecordingAnnotation.objects.filter(nabat_recording=nabat_recording_id)

    if user_email:
        fileAnnotations = fileAnnotations.filter(
            Q(user_email=user_email) | Q(user_email__isnull=True)
        )

    fileAnnotations = fileAnnotations.order_by('confidence')

    output = [
        NABatRecordingAnnotationSchema.from_orm(fileAnnotation).dict()
        for fileAnnotation in fileAnnotations
    ]
    return output


@router.get('recording-annotation/{id}', auth=None, response=NABatRecordingAnnotationSchema)
def get_recording_annotation(request: HttpRequest, id: int, apiToken: str):
    token_data = decode_jwt(apiToken)
    user_email = token_data['email']
    try:
        annotation = NABatRecordingAnnotation.objects.get(pk=id)

        if user_email:
            annotation = annotation.filter(Q(user_email=user_email) | Q(user_email__isnull=True))

        return NABatRecordingAnnotationSchema.from_orm(annotation).dict()
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({'error': 'Recording annotation not found.'}, 404)


@router.get(
    'recording-annotation/{id}/details', auth=None, response=NABatRecordingAnnotationDetailsSchema
)
def get_recording_annotation_details(request: HttpRequest, id: int, apiToken: str):
    token_data = decode_jwt(apiToken)
    user_email = token_data['email']
    try:
        annotation = NABatRecordingAnnotation.objects.get(
            Q(pk=id) & (Q(user_email=user_email) | Q(user_email__isnull=True))
        )

        return NABatRecordingAnnotationDetailsSchema.from_orm(annotation).dict()
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({'error': 'Recording annotation not found.'}, 404)


@router.put('recording-annotation', auth=None, response={200: str})
def create_recording_annotation(request: HttpRequest, data: NABatCreateRecordingAnnotationSchema):
    token_data = decode_jwt(data.apiToken)
    user_id = token_data['sub']
    user_email = token_data['email']

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
        if len(data.species) > 0:
            species_id = data.species[0]
            headers = {
                'Authorization': f'Bearer {data.apiToken}',
                'Content-Type': 'application/json',
            }
            batch_query = UPDATE_QUERY % {
                'survey_event_id': recording.survey_event_id,
                'software_id': SOFTWARE_ID,
                'acoustic_file_id': recording.recording_id,
                'species_id': species_id,
            }
            try:
                response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
                logger.info(response.json())
            except Exception as e:
                logger.error(f'API Request Failed: {e}')
                return JsonResponse({'error': 'Failed to connect to NABat API'}, status=500)

        return 'Recording annotation created successfully.'
    except NABatRecording.DoesNotExist:
        return JsonResponse({'error': 'Recording not found.'}, 404)
    except Species.DoesNotExist:
        return JsonResponse({'error': 'One or more species IDs not found.'}, 404)


@router.patch('recording-annotation/{id}', auth=None, response={200: str})
def update_recording_annotation(
    request: HttpRequest, id: int, data: NABatCreateRecordingAnnotationSchema
):
    token_data = decode_jwt(data.apiToken)
    user_email = token_data['email']

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

        if len(data.species) > 0:
            species_id = data.species[0]
            headers = {
                'Authorization': f'Bearer {data.apiToken}',
                'Content-Type': 'application/json',
            }
            batch_query = UPDATE_QUERY % {
                'survey_event_id': annotation.nabat_recording.survey_event_id,
                'software_id': SOFTWARE_ID,
                'acoustic_file_id': annotation.nabat_recording.recording_id,
                'species_id': species_id,
            }
            try:
                response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
                json_response = response.json()
                if json_response.get('errors'):
                    logger.error(f'API Error: {json_response["errors"]}')
                    return JsonResponse(json_response, status=500)
            except Exception as e:
                logger.error(f'API Request Failed: {e}')
                return JsonResponse({'error': 'Failed to connect to NABat API'}, status=500)

        annotation.save()
        return 'Recording annotation updated successfully.'
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({'error': 'Recording not found.'}, 404)
    except Species.DoesNotExist:
        return JsonResponse({'error': 'One or more species IDs not found.'}, 404)


@router.delete('recording-annotation/{id}', auth=None, response={200: str})
def delete_recording_annotation(request: HttpRequest, id: int, apiToken: str):
    token_data = decode_jwt(apiToken)
    user_email = token_data['email']
    try:
        annotation = NABatRecordingAnnotation.objects.get(pk=id, user_email=user_email)

        # Check permission
        annotation.delete()
        return 'Recording annotation deleted successfully.'
    except NABatRecordingAnnotation.DoesNotExist:
        return JsonResponse({'error': 'Recording not found for this user.'}, 404)
