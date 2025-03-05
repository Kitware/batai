import logging

from django.http import HttpRequest
from ninja import Form, Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import ProcessingTask, colormap
from bats_ai.core.models.nabat import (
    AcousticBatch,
    AcousticBatchAnnotation,
    NABatCompressedSpectrogram,
)
from bats_ai.core.views.species import SpeciesSchema
from bats_ai.tasks.nabat.nabat_data_retrieval import acoustic_batch_initialize
from bats_ai.tasks.tasks import predict_compressed

logger = logging.getLogger(__name__)


router = RouterPaginated()


class AcousticBatchSchema(Schema):
    name: str
    batch_id: int
    recorded_date: str | None
    equipment: str | None
    comments: str | None
    recording_location: str | None
    grts_cell_id: int | None
    grts_cell: int | None


class AcousticBatchGenerateSchema(Schema):
    apiToken: str
    batchId: int


class AcousticBatchAnnotationSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    confidence: float
    id: int | None = None

    @classmethod
    def from_orm(cls, obj: AcousticBatchAnnotation, **kwargs):
        return cls(
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
            confidence=obj.confidence,
            comments=obj.comments,
            model=obj.model,
            id=obj.pk,
        )


@router.post('/')
def generate_acoustic_batch(
    request: HttpRequest,
    payload: Form[AcousticBatchGenerateSchema],
):
    existing_task = ProcessingTask.objects.filter(
        metadata__batchId=payload.batchId,
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()

    if existing_task:
        return {
            'error': 'A task is already processing this batchId.',
            'taskId': existing_task.celery_id,
            'status': existing_task.status,
        }, 400

    acoustic_batch = AcousticBatch.objects.filter(batch_id=payload.batchId)
    if not acoustic_batch.exists():
        # use a task to start downloading the file using the API key and generate the spectrograms
        task = acoustic_batch_initialize.delay(payload.batchId, payload.apiToken)
        ProcessingTask.objects.create(
            name=f'Processing Acoustic BatchId {payload.batchId}',
            status=ProcessingTask.Status.QUEUED,
            metadata={
                'type': 'AcousticBatchProcessing',
                'batchId': payload.batchId,
            },
            celery_id=task.id,
        )
        return {'taskId': task.id}
    return {'acousticId': acoustic_batch.first().pk}


@router.get('/')
def get_acoustic_batch_spectrogram(request: HttpRequest, id: int):
    try:
        acoustic_batch = AcousticBatch.objects.get(batch_id=id)
    except AcousticBatch.DoesNotExist:
        return {'error': 'AcousticBatch not found'}

    with colormap(None):
        spectrogram = acoustic_batch.spectrogram

    compressed = acoustic_batch.compressed_spectrogram

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

    # Pulse and Sequence Annotations may be implemented in the future
    spectro_data['annotations'] = []
    spectro_data['temporal'] = []
    return spectro_data


@router.get('/{acoustic_batch_id}/recording-annotations')
def get_acoustic_batch_annotation(request: HttpRequest, acoustic_batch_id: int):
    fileAnnotations = AcousticBatchAnnotation.objects.filter(
        acoustic_batch=acoustic_batch_id
    ).order_by('confidence')
    output = [
        AcousticBatchAnnotationSchema.from_orm(fileAnnotation).dict()
        for fileAnnotation in fileAnnotations
    ]
    return output


@router.post('/{id}/spectrogram/compressed/predict')
def predict_spectrogram_compressed(request: HttpRequest, id: int):
    try:
        recording = AcousticBatch.objects.get(pk=id)
        compressed_spectrogram = NABatCompressedSpectrogram.objects.filter(
            acoustic_batch=id
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
        acoustic_batch = AcousticBatch.objects.get(pk=id)
    except AcousticBatch.DoesNotExist:
        return {'error': 'Recording not found'}

    with colormap(None):
        spectrogram = acoustic_batch.spectrogram

    compressed = acoustic_batch.compressed_spectrogram

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


@router.get('/{id}/spectrogram/compressed')
def get_spectrogram_compressed(request: HttpRequest, id: int):
    try:
        acoustic_batch = AcousticBatch.objects.get(pk=id)
        compressed_spectrogram = NABatCompressedSpectrogram.objects.filter(
            acoustic_batch=id
        ).first()
    except compressed_spectrogram.DoesNotExist:
        return {'error': 'Compressed Spectrogram'}
    except acoustic_batch.DoesNotExist:
        return {'error': 'Recording does not exist'}

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
    }

    # Serialize the annotations using AnnotationSchema
    annotations_data = []
    temporal_annotations_data = []

    spectro_data['annotations'] = annotations_data
    spectro_data['temporal'] = temporal_annotations_data
    return spectro_data
