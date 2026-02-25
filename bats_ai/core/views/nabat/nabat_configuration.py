from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import logging
from typing import Any, Literal
import uuid

from django.contrib.gis.db.models import functions as gis_functions
from django.contrib.gis.geos import Point, Polygon
from django.db import transaction
from django.db.models import Count
from django.http import HttpRequest, JsonResponse
from django.utils.timezone import now
from ninja import Query, Router, Schema
from ninja.pagination import paginate

from bats_ai.core.models import ExportedAnnotationFile, ProcessingTask, ProcessingTaskType
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation
from bats_ai.core.tasks.nabat.nabat_export_task import export_nabat_annotations_task
from bats_ai.core.tasks.nabat.nabat_update_species import update_nabat_species

logger = logging.getLogger(__name__)

router = Router()


@router.post("/update-species")
def update_species_list(request: HttpRequest):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Permission denied"}, status=403)
    existing_task = ProcessingTask.objects.filter(
        metadata__type=ProcessingTaskType.UPDATING_SPECIES.value,
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()

    if existing_task:
        return JsonResponse(
            {
                "error": "A task is already updating the Species List.",
                "taskId": existing_task.celery_id,
                "status": existing_task.status,
            },
            status=409,
        )

    task = update_nabat_species.delay()
    with transaction.atomic():
        ProcessingTask.objects.create(
            name="Updating Species List",
            status=ProcessingTask.Status.QUEUED,
            metadata={
                "type": ProcessingTaskType.UPDATING_SPECIES.value,
            },
            celery_id=task.id,
        )
    return {"taskId": task.id}


class RecordingFilterSchema(Schema):
    survey_event_id: int | None = None
    recording_id: int | None = None
    bbox: list[float] | None = None  # [minX, minY, maxX, maxY]
    location: tuple[float, float] | None = None  # (lat, lon)
    radius: float | None = None  # meters
    sort_by: Literal["created", "annotation_count", "survey_event_id", "recording_id"] | None = (
        "created"  # default sort field
    )
    sort_direction: Literal["asc", "desc"] | None = "desc"  # 'asc' or 'desc'


class RecordingListItemSchema(Schema):
    id: int
    recording_id: int | None
    survey_event_id: int | None
    acoustic_batch_id: int | None
    name: str
    created: datetime | None
    recording_location: dict[str, Any] | None
    annotation_count: int | None


@router.get("/recordings", response=list[RecordingListItemSchema])
@paginate
def list_recordings(request: HttpRequest, filters: Query[RecordingFilterSchema]):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Permission denied"}, status=403)

    recordings = NABatRecording.objects.annotate(
        annotation_count=Count("nabatrecordingannotation"),
    ).prefetch_related("computed_species", "nabat_auto_species")

    if filters.survey_event_id:
        recordings = recordings.filter(survey_event_id=filters.survey_event_id)
    if filters.recording_id:
        recordings = recordings.filter(recording_id=filters.recording_id)

    if filters.bbox:
        if len(filters.bbox) != 4:
            return JsonResponse(
                {"error": "Invalid bbox format. Expected [minX, minY, maxX, maxY]."}, status=400
            )
        minx, miny, maxx, maxy = filters.bbox
        bbox_poly = Polygon.from_bbox((minx, miny, maxx, maxy))
        recordings = recordings.filter(recording_location__intersects=bbox_poly)

    if filters.location and filters.radius:
        lat, lon = filters.location
        point = Point(lon, lat, srid=4326)
        recordings = recordings.annotate(
            distance=gis_functions.Distance("recording_location", point)
        ).filter(recording_location__distance_lte=(point, filters.radius))

    sort_field = filters.sort_by or "created"
    if sort_field not in ["created", "annotation_count", "recording_id"]:
        sort_field = "created"

    sort_prefix = "" if filters.sort_direction == "asc" else "-"
    recordings = recordings.order_by(f"{sort_prefix}{sort_field}")

    return [
        {
            "id": rec.id,
            "name": rec.name,
            "annotation_count": rec.annotation_count,
            "created": rec.created,
            "recording_id": rec.recording_id,
            "survey_event_id": rec.survey_event_id,
            "acoustic_batch_id": rec.acoustic_batch_id,
            "recording_location": (
                json.loads(rec.recording_location.geojson) if rec.recording_location else None
            ),
        }
        for rec in recordings
    ]


class AnnotationFilterSchema(Schema):
    sort_by: Literal["created", "user_email", "confidence"] | None = "created"  # default sort field
    sort_direction: Literal["asc", "desc"] | None = "desc"  # 'asc' or 'desc'


class AnnotationSchema(Schema):
    id: int
    comments: str | None
    confidence: float | None
    created: datetime
    user_id: uuid.UUID | None
    user_email: str | None
    species: list[str] | None
    model: str | None


@router.get("/recordings/{recording_id}/annotations", response=list[AnnotationSchema])
@paginate
def recording_annotations(
    request: HttpRequest, recording_id: int, filters: Query[AnnotationFilterSchema]
):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Permission denied"}, status=403)

    try:
        recording = NABatRecording.objects.get(pk=recording_id)
    except NABatRecording.DoesNotExist:
        return JsonResponse({"error": "Recording not found"}, status=404)

    annotations = NABatRecordingAnnotation.objects.filter(nabat_recording=recording)

    sort_field = filters.sort_by or "created"
    if sort_field not in ["created", "user_email", "confidence"]:
        sort_field = "created"

    sort_prefix = "" if filters.sort_direction == "asc" else "-"
    annotations = annotations.order_by(f"{sort_prefix}{sort_field}")

    return [
        {
            "id": annotation.id,
            "comments": annotation.comments,
            "confidence": annotation.confidence,
            "created": annotation.created,
            "user_id": annotation.user_id or None,
            "user_email": annotation.user_email or None,
            "species": [species.species_code for species in annotation.species.all()],
            "model": annotation.model or None,
        }
        for annotation in annotations
    ]


@router.get("/stats")
def get_stats(request: HttpRequest):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Permission denied"}, status=403)

    total_recordings = NABatRecording.objects.count()
    total_annotations = NABatRecordingAnnotation.objects.count()

    return {
        "total_recordings": total_recordings,
        "total_annotations": total_annotations,
    }


class AnnotationExportRequest(Schema):
    start_date: date | None = None
    end_date: date | None = None
    recording_ids: list[int] | None = None
    usernames: list[str] | None = None
    min_confidence: float | None = None
    max_confidence: float | None = None


@router.post(
    "/export",
)
def export_annotations(request: HttpRequest, filters: AnnotationExportRequest):
    export = ExportedAnnotationFile.objects.create(
        filters_applied=filters.dict(),
        status="pending",
        expires_at=now() + timedelta(hours=24),
    )
    export_nabat_annotations_task.delay(filters.dict(), export.id)
    return export.id
