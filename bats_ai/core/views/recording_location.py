from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Literal

from django.db.models import Q, QuerySet
from ninja import Query, Router, Schema
from ninja.errors import HttpError

from bats_ai.core.models import Configuration, GRTSCells, Recording, RecordingAnnotation

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)

router = Router()

_GRTS_CUSTOM_ORDER: list[int] = GRTSCells.sort_order()
_GRTS_ORDER_MAP: dict[int, int] = {frame_id: idx for idx, frame_id in enumerate(_GRTS_CUSTOM_ORDER)}


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


def _apply_recording_filters_and_sort(
    *,
    qs: QuerySet[Recording],
    request: HttpRequest,
    exclude_submitted: bool | None,
    tags: str | None,
) -> QuerySet[Recording]:
    if exclude_submitted:
        submitted_by_user = RecordingAnnotation.objects.filter(
            owner=request.user, submitted=True
        ).values_list("recording_id", flat=True)
        qs = qs.exclude(pk__in=submitted_by_user)

    tag_list = _split_tags(tags)
    if tag_list:
        for tag in tag_list:
            qs = qs.filter(tags__text=tag)
        qs = qs.distinct()

    # Keep deterministic ordering even though we don't expose sorting params.
    return qs.order_by("-created")


def _coords_in_bbox(
    coords: list[float],
    *,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
) -> bool:
    lon, lat = coords
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


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
    if not recording.recording_location:
        return None

    # GeoDjango geometry -> GeoJSON -> coordinates.
    location_geojson = json.loads(recording.recording_location.json)
    coords = location_geojson.get("coordinates")
    if (
        isinstance(coords, list)
        and len(coords) == 2
        and all(isinstance(v, (int, float)) for v in coords)
    ):
        return [float(coords[0]), float(coords[1])]
    return None


def _precompute_grts_cell_centroids(cell_ids: set[int]) -> dict[int, list[float]]:
    """Precompute centroid coordinates for each `grts_cell_id`.

    Choose the same "best" cell as `core/views/grts_cells.py` does, then compute
    `[lon, lat]` from its centroid.
    """
    if not cell_ids:
        return {}

    centroids: dict[int, list[float]] = {}

    cells = GRTSCells.objects.filter(grts_cell_id__in=cell_ids)
    cells_by_id: dict[int, list[GRTSCells]] = {}
    for cell in cells:
        cells_by_id.setdefault(cell.grts_cell_id, []).append(cell)

    for cell_id in cell_ids:
        candidates = cells_by_id.get(cell_id, [])
        if not candidates:
            continue

        # Pick the same "best" cell as core/views/grts_cells.py.
        best = sorted(
            candidates,
            key=lambda c: _GRTS_ORDER_MAP.get(c.sample_frame_id, len(_GRTS_CUSTOM_ORDER)),
        )[0]

        # Prefer the stored centroid (computed during GRTS import / migrations).
        if best.centroid_4326 is None:
            continue

        centroids[cell_id] = [float(best.centroid_4326.x), float(best.centroid_4326.y)]

    return centroids


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
        Q(owner=request.user) | Q(spectrogram__isnull=True)
    )

    my_qs = _apply_recording_filters_and_sort(
        qs=my_qs,
        request=request,
        exclude_submitted=q.exclude_submitted,
        tags=q.tags,
    )
    shared_qs = _apply_recording_filters_and_sort(
        qs=shared_qs,
        request=request,
        exclude_submitted=q.exclude_submitted,
        tags=q.tags,
    )

    # Evaluate querysets: we need in-Python centroid/geojson conversion.
    my_list = list(my_qs)
    shared_list = list(shared_qs)
    recordings = my_list + shared_list

    required_cell_ids = {r.grts_cell_id for r in recordings if r.grts_cell_id is not None}
    centroids_by_cell_id = _precompute_grts_cell_centroids(required_cell_ids)

    bbox = _parse_bbox(q.bbox)

    features: list[dict[str, Any]] = []
    for rec in recordings:
        coords: list[float] | None = None

        if vetting_enabled:
            # when vetting is enabled, we only show the centroid of the grts cell
            # and not the direct recording location
            if rec.grts_cell_id is not None:
                coords = centroids_by_cell_id.get(rec.grts_cell_id)
            # If we can't resolve a centroid, fall back to recording_location if present.
            if coords is None:
                coords = _get_recording_location_coords(rec)
        else:
            coords = _get_recording_location_coords(rec)
            if coords is None and rec.grts_cell_id is not None:
                coords = centroids_by_cell_id.get(rec.grts_cell_id)

        if coords is None:
            continue

        if bbox is not None and not _coords_in_bbox(
            coords,
            min_lon=bbox[0],
            min_lat=bbox[1],
            max_lon=bbox[2],
            max_lat=bbox[3],
        ):
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
