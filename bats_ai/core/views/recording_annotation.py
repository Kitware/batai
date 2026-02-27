from __future__ import annotations

import logging

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from bats_ai.core.models import Configuration, Recording, RecordingAnnotation, Species
from bats_ai.core.models.recording_annotation import RecordingAnnotationSpecies
from bats_ai.core.views.recording import SpeciesSchema

logger = logging.getLogger(__name__)

router = Router()


# Schemas for serialization
class RecordingAnnotationSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    owner: str
    confidence: float
    id: int | None = None
    submitted: bool
    hasDetails: bool

    @classmethod
    def from_orm(cls, obj: RecordingAnnotation, **kwargs):
        # Ordered list with duplicates via through model
        species_ordered = obj.recordingannotationspecies_set.order_by("order")
        species_list = [t.species for t in species_ordered]
        return cls(
            species=[SpeciesSchema.from_orm(s) for s in species_list],
            owner=obj.owner.username,
            confidence=obj.confidence,
            comments=obj.comments,
            model=obj.model,
            id=obj.pk,
            hasDetails=obj.additional_data is not None,
            submitted=obj.submitted,
        )


# TODO: do we really need this? why can't we just always return the details?
class RecordingAnnotationDetailsSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    owner: str
    confidence: float
    id: int | None = None
    details: dict
    hasDetails: bool
    submitted: bool

    @classmethod
    def from_orm(cls, obj: RecordingAnnotation, **kwargs):
        species_ordered = obj.recordingannotationspecies_set.order_by("order")
        species_list = [t.species for t in species_ordered]
        return cls(
            species=[SpeciesSchema.from_orm(s) for s in species_list],
            owner=obj.owner.username,
            confidence=obj.confidence,
            comments=obj.comments,
            model=obj.model,
            hasDetails=obj.additional_data is not None,
            details=obj.additional_data,
            id=obj.pk,
            submitted=obj.submitted,
        )


class CreateRecordingAnnotationSchema(Schema):
    recordingId: int
    species: list[int]
    comments: str = None
    model: str = None
    confidence: float


class UpdateRecordingAnnotationSchema(Schema):
    species: list[int] = None
    comments: str = None
    model: str = None
    confidence: float = None


@router.get("/{id}", response=RecordingAnnotationSchema)
def get_recording_annotation(request: HttpRequest, id: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission
        if annotation.recording.owner != request.user and not annotation.recording.public:
            raise HttpError(403, "Permission denied.")

        return RecordingAnnotationSchema.from_orm(annotation).dict()
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e


@router.get("/{id}/details", response=RecordingAnnotationDetailsSchema)
def get_recording_annotation_details(request: HttpRequest, id: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission
        if annotation.recording.owner != request.user and not annotation.recording.public:
            raise HttpError(403, "Permission denied.")

        return RecordingAnnotationDetailsSchema.from_orm(annotation).dict()
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e


@router.put("/", response={200: str})
def create_recording_annotation(request: HttpRequest, data: CreateRecordingAnnotationSchema):
    try:
        recording = Recording.objects.get(pk=data.recordingId)

        # Check permission
        if recording.owner != request.user and not recording.public:
            raise HttpError(403, "Permission denied.")

        # Create the recording annotation
        annotation = RecordingAnnotation.objects.create(
            recording=recording,
            owner=request.user,
            comments=data.comments,
            model=data.model,
            confidence=data.confidence,
        )

        # Add species in order (through model allows duplicates)
        for order, species_id in enumerate(data.species):
            species = Species.objects.get(pk=species_id)
            RecordingAnnotationSpecies.objects.create(
                recording_annotation=annotation,
                species=species,
                order=order,
            )

        return "Recording annotation created successfully."
    except Recording.DoesNotExist as e:
        raise HttpError(404, "Recording not found.") from e
    except Species.DoesNotExist as e:
        raise HttpError(404, "One or more species IDs not found.") from e


@router.patch("/{id}", response={200: str})
def update_recording_annotation(
    request: HttpRequest, id: int, data: UpdateRecordingAnnotationSchema
):
    try:
        annotation = RecordingAnnotation.objects.select_related(
            "recording", "recording__owner"
        ).get(pk=id)

        # Check permission
        if annotation.owner != request.user:
            raise HttpError(403, "Permission denied.")

        if annotation.recording.owner != request.user and not annotation.recording.public:
            raise HttpError(403, "Permission denied.")

        # Update fields if provided
        if data.comments is not None:
            annotation.comments = data.comments
        if data.model is not None:
            annotation.model = data.model
        if data.confidence is not None:
            annotation.confidence = data.confidence
        if data.species is not None:
            # Rebuild ordered species with duplicates via through model
            unique_ids = set(data.species)
            id_to_species = {s.pk: s for s in Species.objects.filter(pk__in=unique_ids)}
            if len(id_to_species) != len(unique_ids):
                raise HttpError(404, "One or more species IDs not found.")
            RecordingAnnotationSpecies.objects.filter(recording_annotation=annotation).delete()
            for order, species_id in enumerate(data.species):
                species = id_to_species[species_id]
                RecordingAnnotationSpecies.objects.create(
                    recording_annotation=annotation,
                    species=species,
                    order=order,
                )

        annotation.save()
        return "Recording annotation updated successfully."
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e
    except Species.DoesNotExist as e:
        raise HttpError(404, "One or more species IDs not found.") from e


# DELETE Endpoint
@router.delete("/{id}", response={200: str})
def delete_recording_annotation(request: HttpRequest, id: int):
    try:
        configuration = Configuration.objects.first()
        vetting_enabled = (
            configuration.mark_annotations_completed_enabled if configuration else False
        )
        if vetting_enabled and not request.user.is_staff:
            raise HttpError(
                403, "Permission denied. Annotations cannot be deleted while vetting is enabled"
            )

        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission: only the annotation owner may delete their own
        if annotation.owner != request.user:
            raise HttpError(403, "Permission denied.")

        annotation.delete()
        return "Recording annotation deleted successfully."
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e


# Submit endpoint
@router.patch("/{id}/submit", response={200: dict})
def submit_recording_annotation(request: HttpRequest, id: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission
        if annotation.owner != request.user:
            raise HttpError(403, "Permission denied.")

        annotation.submitted = True
        annotation.save()
        return {
            "id": id,
            "submitted": annotation.submitted,
        }
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e
