from __future__ import annotations

from django.db.models import (
    BooleanField,
    Case,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Value,
    When,
)
from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import GRTSCells, Recording, Species, SpeciesRange

router = RouterPaginated()

# Continental US sample frame ID, defaulting to CONUS GRTS when not specified.
CONUS_SAMPLE_FRAME_ID = 14

_SPECIES_SCHEMA_FIELDS = (
    "species_code",
    "family",
    "genus",
    "species",
    "common_name",
    "species_code_6",
    "category",
    "pk",
)


class SpeciesSchema(Schema):
    species_code: str | None
    family: str | None
    genus: str | None
    species: str | None
    common_name: str | None
    species_code_6: str | None
    category: str | None = None
    pk: int | None = None
    in_range: bool | None = None


def _primary_grts_cell(grts_cell_id: int) -> GRTSCells:
    order = GRTSCells.sort_order()
    whens = [When(sample_frame_id=sid, then=Value(rank)) for rank, sid in enumerate(order)]
    cell = (
        GRTSCells.objects.filter(grts_cell_id=grts_cell_id)
        .exclude(geom_4326__isnull=True)
        .annotate(
            frame_rank=Case(
                *whens,
                default=Value(len(order)),
                output_field=IntegerField(),
            ),
        )
        .order_by("frame_rank")
        .first()
    )
    if cell is None:
        raise Http404(f"No GRTS cell geometry found for grts_cell_id={grts_cell_id}")
    return cell


def _species_values_qs(qs):
    """Restrict columns to SpeciesSchema (excluding optional in_range)."""
    return qs.annotate(pk=F("id")).values(*_SPECIES_SCHEMA_FIELDS)


@router.get("/", response=list[SpeciesSchema], auth=None)
def get_species(
    request: HttpRequest,
    grts_cell_id: int | None = Query(None),
    sample_frame_id: int = Query(CONUS_SAMPLE_FRAME_ID),
    recording_id: int | None = Query(None),
):
    if recording_id is not None:
        recording = get_object_or_404(
            Recording.objects.only("grts_cell_id", "sample_frame_id"),
            pk=recording_id,
        )
        grts_cell_id = recording.grts_cell_id
        sample_frame_id = (
            recording.sample_frame_id
            if recording.sample_frame_id is not None
            else CONUS_SAMPLE_FRAME_ID
        )

    null_in_range = Value(None, output_field=BooleanField(null=True))

    if grts_cell_id is None:
        qs = Species.objects.annotate(
            pk=F("id"),
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
                pk=F("id"),
                in_range=null_in_range,
            )
        else:
            overlaps_cell = SpeciesRange.objects.filter(
                species_id=OuterRef("id"),
                geom__intersects=cell_geom,
            )
            qs = Species.objects.annotate(
                pk=F("id"),
                in_range=Case(
                    When(Exists(overlaps_cell), then=Value(True)),
                    default=null_in_range,
                    output_field=BooleanField(null=True),
                ),
            )

    return list(
        qs.order_by("species_code").values(
            *_SPECIES_SCHEMA_FIELDS,
            "in_range",
        )
    )
