from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ninja import Router, Schema
from ninja.errors import HttpError

from bats_ai.core.models import Configuration, Recording, RecordingAnnotation, Species
from bats_ai.core.views.recording import SpeciesSchema

if TYPE_CHECKING:
    from django.http import HttpRequest

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
    def from_orm(cls, obj: RecordingAnnotation):
        return cls(
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
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
    def from_orm(cls, obj: RecordingAnnotation):
        return cls(
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
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


@router.get("/{pk}", response=RecordingAnnotationSchema)
def get_recording_annotation(request: HttpRequest, pk: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=pk)

        # Check permission
        if annotation.recording.owner != request.user and not annotation.recording.public:
            raise HttpError(403, "Permission denied.")

        return RecordingAnnotationSchema.from_orm(annotation).dict()
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e


@router.get("/{pk}/details", response=RecordingAnnotationDetailsSchema)
def get_recording_annotation_details(request: HttpRequest, pk: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=pk)

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

        # Add species
        for species_id in data.species:
            species = Species.objects.get(pk=species_id)
            annotation.species.add(species)

        return "Recording annotation created successfully."
    except Recording.DoesNotExist as e:
        raise HttpError(404, "Recording not found.") from e
    except Species.DoesNotExist as e:
        raise HttpError(404, "One or more species IDs not found.") from e


@router.patch("/{pk}", response={200: str})
def update_recording_annotation(
    request: HttpRequest, pk: int, data: UpdateRecordingAnnotationSchema
):
    try:
        annotation = RecordingAnnotation.objects.select_related(
            "recording", "recording__owner"
        ).get(pk=pk)

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
            species_list = list(Species.objects.filter(pk__in=data.species))
            if len(species_list) != len(data.species):
                raise HttpError(404, "One or more species IDs not found.")
            annotation.species.set(species_list)

        annotation.save()
        return "Recording annotation updated successfully."
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e
    except Species.DoesNotExist as e:
        raise HttpError(404, "One or more species IDs not found.") from e


# DELETE Endpoint
@router.delete("/{pk}", response={200: str})
def delete_recording_annotation(request: HttpRequest, pk: int):
    try:
        configuration = Configuration.objects.first()
        vetting_enabled = (
            configuration.mark_annotations_completed_enabled if configuration else False
        )
        if vetting_enabled and not request.user.is_staff:
            raise HttpError(
                403, "Permission denied. Annotations cannot be deleted while vetting is enabled"
            )

        annotation = RecordingAnnotation.objects.get(pk=pk)

        # Check permission: only the annotation owner may delete their own
        if annotation.owner != request.user:
            raise HttpError(403, "Permission denied.")

        annotation.delete()
        return "Recording annotation deleted successfully."
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e


# Submit endpoint
@router.patch("/{pk}/submit", response={200: dict})
def submit_recording_annotation(request: HttpRequest, pk: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=pk)

        # Check permission
        if annotation.owner != request.user:
            raise HttpError(403, "Permission denied.")

        annotation.submitted = True
        annotation.save()
        return {
            "id": pk,
            "submitted": annotation.submitted,
        }
    except RecordingAnnotation.DoesNotExist as e:
        raise HttpError(404, "Recording annotation not found.") from e
