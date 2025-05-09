from datetime import datetime
import logging

from django.contrib.gis.db.models import functions as gis_functions
from django.contrib.gis.geos import Point, Polygon
from django.db.models import Count
from django.http import HttpRequest, JsonResponse
from ninja import Query, Router, Schema
from ninja.pagination import paginate

from bats_ai.core.models import ProcessingTask, ProcessingTaskType
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation
from bats_ai.tasks.nabat.nabat_update_species import update_nabat_species

logger = logging.getLogger(__name__)

router = Router()


@router.post('/update-species')
def update_species_list(request: HttpRequest):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    existing_task = ProcessingTask.objects.filter(
        metadata__type=ProcessingTaskType.UPDATING_SPECIES.value,
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()

    if existing_task:
        return JsonResponse(
            {
                'error': 'A task is already updating the Species List.',
                'taskId': existing_task.celery_id,
                'status': existing_task.status,
            },
            status=409,
        )

    task = update_nabat_species.delay()
    ProcessingTask.objects.create(
        name='Updating Species List',
        status=ProcessingTask.Status.QUEUED,
        metadata={
            'type': ProcessingTaskType.UPDATING_SPECIES.value,
        },
        celery_id=task.id,
    )
    return {'taskId': task.id}


class RecordingFilterSchema(Schema):
    survey_event_id: int | None = None
    recording_id: int | None = None
    bbox: list[float] | None = None  # [minX, minY, maxX, maxY]
    location: tuple[float, float] | None = None  # (lat, lon)
    radius: float | None = None  # meters


class RecordingListItemSchema(Schema):
    id: int
    filename: str
    site_id: int | None
    site_name: str | None
    location: str | None
    nabat_auto_species: list[str] | None  # Adjust type if needed


@router.get('/recordings', response=list[RecordingListItemSchema])
@paginate
def list_recordings(request: HttpRequest, filters: Query[RecordingFilterSchema]):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    recordings = NABatRecording.objects.annotate(
        annotation_count=Count('nabatrecordingannotation'),
    ).prefetch_related('computed_species', 'nabat_auto_species')

    if filters.survey_event_id:
        recordings = recordings.filter(survey_event_id=filters.survey_event_id)
    if filters.recording_id:
        recordings = recordings.filter(recording_id=filters.recording_id)

    if filters.bbox:
        if len(filters.bbox) != 4:
            return JsonResponse(
                {'error': 'Invalid bbox format. Expected [minX, minY, maxX, maxY].'}, status=400
            )
        minx, miny, maxx, maxy = filters.bbox
        bbox_poly = Polygon.from_bbox((minx, miny, maxx, maxy))
        recordings = recordings.filter(recording_location__intersects=bbox_poly)

    if filters.location and filters.radius:
        lat, lon = filters.location
        point = Point(lon, lat, srid=4326)
        recordings = recordings.annotate(
            distance=gis_functions.Distance('recording_location', point)
        ).filter(recording_location__distance_lte=(point, filters.radius))

    return [
        {
            'id': rec.id,
            'recording_id': rec.recording_id,
            'survey_event_id': rec.survey_event_id,
            'computed_species': [species.name for species in rec.computed_species.all()],
            'annotation_count': rec.annotation_count,
            'name': rec.name,
            'created': rec.created,
            'recording_location': rec.recording_location.geojson
            if rec.recording_location
            else None,
            'nabat_auto_species': rec.nabat_auto_species.name if rec.nabat_auto_species else None,
        }
        for rec in recordings
    ]


class AnnotationSchema(Schema):
    id: int
    comments: str | None
    confidence: float | None
    created: datetime


@router.get('/recordings/{recording_id}/annotations', response=list[AnnotationSchema])
@paginate
def recording_annotations(request: HttpRequest, recording_id: int):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        recording = NABatRecording.objects.get(recording_id=recording_id)
    except NABatRecording.DoesNotExist:
        return JsonResponse({'error': 'Recording not found'}, status=404)

    annotations = NABatRecordingAnnotation.objects.filter(nabat_recording=recording)
    return [
        {
            'id': annotation.id,
            'comments': annotation.comments,
            'confidence': annotation.confidence,
            'created': annotation.created,
        }
        for annotation in annotations
    ]


@router.get('/stats')
def get_stats(request: HttpRequest):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    total_recordings = NABatRecording.objects.count()
    total_annotations = NABatRecordingAnnotation.objects.count()

    return {
        'total_recordings': total_recordings,
        'total_annotations': total_annotations,
    }
