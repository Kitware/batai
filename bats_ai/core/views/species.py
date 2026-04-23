from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import (
    BooleanField,
    Case,
    Exists,
    OuterRef,
    Value,
    When,
)
from django.shortcuts import get_object_or_404
from ninja import Query, Router, Schema

from bats_ai.core.models import GRTSCells, Recording, Species, SpeciesRange
from bats_ai.core.utils.grts_utils import normalize_sample_frame_id

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router()

# Continental US sample frame ID, defaulting to CONUS GRTS when not specified.
CONUS_SAMPLE_FRAME_ID = 14


class SpeciesSchema(Schema):
    species_code: str | None
    family: str | None
    genus: str | None
    species: str | None
    common_name: str | None
    species_code_6: str | None
    category: str | None = None
    pk: int | None = None
    # in_range indicates whether the species' range intersects the specified GRTS cell Id
    # True: if grts_cell_id geometry exists and intercepts the species range geometry
    # False: if grts_cell_id geometry exists but does not intersect the species range
    # None: if grts_cell_id geometry does not exist
    in_range: bool | None = None


@router.get("/", response=list[SpeciesSchema], auth=None)
def get_species(
    request: HttpRequest,
    grts_cell_id: int | None = Query(None),
    sample_frame_id: int = Query(CONUS_SAMPLE_FRAME_ID),
    recording_id: int | None = Query(None),
):
    sample_frame_id = normalize_sample_frame_id(sample_frame_id)

    if recording_id is not None:
        recording = get_object_or_404(
            Recording.objects.only("grts_cell_id", "sample_frame_id"),
            pk=recording_id,
        )
        grts_cell_id = recording.grts_cell_id
        sample_frame_id = normalize_sample_frame_id(
            recording.sample_frame_id
            if recording.sample_frame_id is not None
            else CONUS_SAMPLE_FRAME_ID
        )

    null_in_range = Value(None, output_field=BooleanField(null=True))

    if grts_cell_id is None:
        qs = Species.objects.annotate(
            in_range=null_in_range,
        )
    else:
        cell_geom = (
            GRTSCells.objects.filter(
                grts_cell_id=grts_cell_id,
                sample_frame_id=sample_frame_id,
            )
            .exclude(geom_4326__isnull=True)
            .values_list("geom_4326", flat=True)
            .first()
        )
        if cell_geom is None:
            qs = Species.objects.annotate(
                in_range=null_in_range,
            )
        else:
            overlaps_cell = SpeciesRange.objects.filter(
                species_id=OuterRef("id"),
                geom__intersects=cell_geom,
            )
            qs = Species.objects.annotate(
                in_range=Case(
                    When(Exists(overlaps_cell), then=Value(True)),
                    default=False,
                    output_field=BooleanField(null=True),
                ),
            )

    return qs.order_by("species_code")
