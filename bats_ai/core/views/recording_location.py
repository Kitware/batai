from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from django.contrib.gis.geos import Polygon
from django.db.models import Exists, OuterRef, Q, QuerySet
from ninja import Query, Router, Schema
from ninja.errors import HttpError

from bats_ai.core.models import (
    Configuration,
    GRTSCells,
    Recording,
    RecordingAnnotation,
)
from bats_ai.core.utils.grts_utils import (
    normalize_sample_frame_id,
    recording_effective_sample_frame_id_case,
)

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)

router = Router()


class RecordingLocationsQuerySchema(Schema):
    # When true, exclude recordings the current user has already submitted.
    exclude_submitted: bool | None = None
    # Comma-separated tag texts; recording must have all listed tags.
    tags: str | None = None
    # Bounding box filter (lon/lat) as `[min_lon, min_lat, max_lon, max_lat]`.
    bbox: str | None = None


class RecordingLocationsFeaturePropertiesSchema(Schema):
    recording_id: int
    filename: str


class RecordingLocationsFeatureGeometrySchema(Schema):
    type: Literal["Point"] = "Point"
    coordinates: list[float]


class RecordingLocationsFeatureSchema(Schema):
    type: Literal["Feature"] = "Feature"
    geometry: RecordingLocationsFeatureGeometrySchema
    properties: RecordingLocationsFeaturePropertiesSchema


class RecordingLocationsResponseSchema(Schema):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[RecordingLocationsFeatureSchema]


def _split_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def filter_recordings_by_map_bbox(
    qs: QuerySet[Recording],
    bbox_poly: Polygon,
) -> QuerySet[Recording]:
    """Keep recordings whose point lies in the bbox or whose GRTS cell centroid matches.

    Cell matching uses ``(grts_cell_id, sample_frame_id)`` on ``GRTSCells``, with the
    same effective sample frame rules as ``normalize_sample_frame_id``.
    """
    cell_centroid_in_bbox = GRTSCells.objects.filter(
        centroid_4326__intersects=bbox_poly,
        grts_cell_id=OuterRef("grts_cell_id"),
        sample_frame_id=OuterRef("_map_bbox_effective_sf"),
    )
    return qs.annotate(_map_bbox_effective_sf=recording_effective_sample_frame_id_case()).filter(
        Q(recording_location__intersects=bbox_poly)
        | (Q(grts_cell_id__isnull=False) & Exists(cell_centroid_in_bbox))
    )


def _apply_recording_filters_and_sort(
    *,
    qs: QuerySet[Recording],
    exclude_submitted: bool,
    submitted_by_user: QuerySet[int] | None,
    tags: str | None,
    bbox_poly: Polygon | None,
) -> QuerySet[Recording]:
    if exclude_submitted and submitted_by_user is not None:
        qs = qs.exclude(pk__in=submitted_by_user)

    tag_list = _split_tags(tags)
    if tag_list:
        for tag in tag_list:
            qs = qs.filter(tags__text=tag)
        qs = qs.distinct()

    if bbox_poly is not None:
        qs = filter_recordings_by_map_bbox(qs, bbox_poly)

    # Keep deterministic ordering even though we don't expose sorting params.
    return qs.order_by("-created")


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None

    raw = bbox.strip()
    # Allow bbox=lon1,lat1,lon2,lat2
    values = [v.strip() for v in raw.split(",")]

    if not isinstance(values, list) or len(values) != 4:
        raise HttpError(400, "bbox must contain exactly 4 numbers")

    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in values)
    except Exception as e:
        raise HttpError(400, f"bbox values must be numbers: {e}") from e

    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise HttpError(400, "bbox latitude values must be within [-90, 90]")

    # Normalize ordering.
    if min_lon > max_lon:
        min_lon, max_lon = max_lon, min_lon
    if min_lat > max_lat:
        min_lat, max_lat = max_lat, min_lat

    return min_lon, min_lat, max_lon, max_lat


def _get_recording_location_coords(recording: Recording) -> list[float] | None:
    """Return `[lon, lat]` for `Recording.recording_location` if present."""
    point = recording.recording_location
    if not point:
        return None

    # Prefer direct GEOS access instead of serializing geometry to JSON.
    return [float(point.x), float(point.y)]


def _precompute_grts_cell_centroids(
    sample_frame_cell_id_pairs: set[tuple[int, int]],
) -> dict[tuple[int, int], list[float]]:
    """Precompute centroid `[lon, lat]` for each `(sample_frame_id, grts_cell_id)` pair."""
    if not sample_frame_cell_id_pairs:
        return {}

    cell_ids = {cell_id for sample_frame_id, cell_id in sample_frame_cell_id_pairs}
    sample_frame_ids = {sample_frame_id for sample_frame_id, cell_id in sample_frame_cell_id_pairs}
    rows = (
        GRTSCells.objects.filter(
            grts_cell_id__in=cell_ids,
            sample_frame_id__in=sample_frame_ids,
            centroid_4326__isnull=False,
        )
        # DISTINCT ON columns must match the leading ORDER BY columns; `pk`
        # breaks ties if duplicate (grts_cell_id, sample_frame_id) rows exist.
        .order_by("grts_cell_id", "sample_frame_id", "pk")
        .distinct("grts_cell_id", "sample_frame_id")
        .values_list("sample_frame_id", "grts_cell_id", "centroid_4326")
    )

    return {
        (int(sample_frame_id), int(cell_id)): [float(centroid.x), float(centroid.y)]
        for sample_frame_id, cell_id, centroid in rows
        if centroid is not None
    }


@router.get("/", response=RecordingLocationsResponseSchema)
def get_recording_locations(
    request: HttpRequest,
    q: Query[RecordingLocationsQuerySchema],
):
    config = Configuration.objects.first()
    vetting_enabled = bool(config.mark_annotations_completed_enabled) if config else False

    # Build "full" set: my + shared recordings.
    my_qs = Recording.objects.filter(owner=request.user)
    shared_qs = Recording.objects.filter(public=True).exclude(
        Q(owner=request.user) | Q(spectrograms__isnull=True)
    )

    exclude_submitted = bool(q.exclude_submitted)
    submitted_by_user = None
    if exclude_submitted:
        submitted_by_user = RecordingAnnotation.objects.filter(
            owner=request.user, submitted=True
        ).values_list("recording_id", flat=True)

    bbox = _parse_bbox(q.bbox)
    bbox_poly: Polygon | None = None
    if bbox is not None:
        bbox_poly = Polygon.from_bbox((bbox[0], bbox[1], bbox[2], bbox[3]))

    my_qs = _apply_recording_filters_and_sort(
        qs=my_qs,
        exclude_submitted=exclude_submitted,
        submitted_by_user=submitted_by_user,
        tags=q.tags,
        bbox_poly=bbox_poly,
    )
    shared_qs = _apply_recording_filters_and_sort(
        qs=shared_qs,
        exclude_submitted=exclude_submitted,
        submitted_by_user=submitted_by_user,
        tags=q.tags,
        bbox_poly=bbox_poly,
    )

    my_list = list(
        my_qs.only(
            "id",
            "audio_file",
            "recording_location",
            "grts_cell_id",
            "sample_frame_id",
            "created",
        )
    )
    shared_list = list(
        shared_qs.only(
            "id",
            "audio_file",
            "recording_location",
            "grts_cell_id",
            "sample_frame_id",
            "created",
        )
    )
    recordings = my_list + shared_list

    sample_frame_cell_id_pairs = {
        (normalize_sample_frame_id(r.sample_frame_id), r.grts_cell_id)
        for r in recordings
        if r.grts_cell_id is not None
    }
    cell_centroids_by_sample_frame_id = _precompute_grts_cell_centroids(sample_frame_cell_id_pairs)

    features: list[dict[str, Any]] = []
    for rec in recordings:
        coords: list[float] | None = None
        sample_frame_for_grts = normalize_sample_frame_id(rec.sample_frame_id)

        if vetting_enabled:
            # When vetting is enabled, we only show the centroid of the
            # GRTS cell and not the direct recording location.
            if rec.grts_cell_id is not None and sample_frame_for_grts is not None:
                coords = cell_centroids_by_sample_frame_id.get(
                    (sample_frame_for_grts, rec.grts_cell_id)
                )
            # If we can't resolve a centroid, fall back to recording_location.
            if coords is None:
                coords = _get_recording_location_coords(rec)
        else:
            coords = _get_recording_location_coords(rec)
            if (
                coords is None
                and rec.grts_cell_id is not None
                and sample_frame_for_grts is not None
            ):
                coords = cell_centroids_by_sample_frame_id.get(
                    (sample_frame_for_grts, rec.grts_cell_id)
                )

        if coords is None:
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords},
                "properties": {
                    "recording_id": rec.id,
                    "filename": str(rec.audio_file),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
