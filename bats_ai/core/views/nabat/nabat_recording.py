import json
import logging
from uuid import UUID

from django.http import HttpRequest, JsonResponse
from ninja import Form, Schema
from ninja.pagination import RouterPaginated
import requests

from bats_ai.core.models import ProcessingTask, colormap
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

BASE_URL = 'https://api.sciencebase.gov/nabat-graphql/graphql'
QUERY = """
query fetchAcousticAndSurveyEventInfo {
  presignedUrlFromAcousticFile(acousticFileId: "%(acoustic_file_id)s") {
    s3PresignedUrl
  }
}
"""


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


class NABatRecordingAnnotationSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    confidence: float
    id: int | None = None

    @classmethod
    def from_orm(cls, obj: NABatRecordingAnnotation, **kwargs):
        return cls(
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
            confidence=obj.confidence,
            comments=obj.comments,
            model=obj.model,
            id=obj.pk,
        )


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
                'type': 'NABatRecordingProcessing',
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


@router.get('/{nabat_recording_id}/recording-annotations')
def get_nabat_recording_annotation(
    request: HttpRequest,
    nabat_recording_id: int,
    user_id: UUID | None = None,
):
    fileAnnotations = NABatRecordingAnnotation.objects.filter(nabat_recording=nabat_recording_id)

    if user_id:
        fileAnnotations = fileAnnotations.filter(user_id=user_id)

    fileAnnotations = fileAnnotations.order_by('confidence')

    output = [
        NABatRecordingAnnotationSchema.from_orm(fileAnnotation).dict()
        for fileAnnotation in fileAnnotations
    ]
    return output


@router.post('/{id}/spectrogram/compressed/predict')
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


@router.get('/{id}/spectrogram')
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
