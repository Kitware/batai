import logging

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from bats_ai.core.models import Recording, RecordingAnnotation, Species

logger = logging.getLogger(__name__)

router = Router()


# Schemas for serialization
class RecordingAnnotationSchema(Schema):
    id: int
    recording: int
    owner: str
    species: list[int]
    comments: str = None
    model: str = None
    confidence: float


class CreateRecordingAnnotationSchema(Schema):
    recording: int
    species: list[int]
    comments: str = None
    model: str = None
    confidence: float


class UpdateRecordingAnnotationSchema(Schema):
    species: list[int] = None
    comments: str = None
    model: str = None
    confidence: float = None


# GET Endpoint
@router.get('/{id}', response=RecordingAnnotationSchema)
def get_recording_annotation(request: HttpRequest, id: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission
        if annotation.recording.owner != request.user and not annotation.recording.public:
            raise HttpError(403, 'Permission denied.')

        return {
            'id': annotation.id,
            'recording': annotation.recording.id,
            'owner': annotation.owner.username,
            'species': [s.id for s in annotation.species.all()],
            'comments': annotation.comments,
            'model': annotation.model,
            'confidence': annotation.confidence,
        }
    except RecordingAnnotation.DoesNotExist:
        raise HttpError(404, 'Recording annotation not found.')


# PUT Endpoint
@router.put('/', response={200: str})
def create_recording_annotation(request: HttpRequest, data: CreateRecordingAnnotationSchema):
    try:
        recording = Recording.objects.get(pk=data.recording)

        # Check permission
        if recording.owner != request.user and not recording.public:
            raise HttpError(403, 'Permission denied.')

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

        return 'Recording annotation created successfully.'
    except Recording.DoesNotExist:
        raise HttpError(404, 'Recording not found.')
    except Species.DoesNotExist:
        raise HttpError(404, 'One or more species IDs not found.')


# PATCH Endpoint
@router.patch('/{id}', response={200: str})
def update_recording_annotation(
    request: HttpRequest, id: int, data: UpdateRecordingAnnotationSchema
):
    try:
        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission
        if annotation.recording.owner != request.user:
            raise HttpError(403, 'Permission denied.')

        # Update fields if provided
        if data.comments is not None:
            annotation.comments = data.comments
        if data.model is not None:
            annotation.model = data.model
        if data.confidence is not None:
            annotation.confidence = data.confidence
        if data.species is not None:
            annotation.species.clear()  # Clear existing species
            for species_id in data.species:
                species = Species.objects.get(pk=species_id)
                annotation.species.add(species)

        annotation.save()
        return 'Recording annotation updated successfully.'
    except RecordingAnnotation.DoesNotExist:
        raise HttpError(404, 'Recording annotation not found.')
    except Species.DoesNotExist:
        raise HttpError(404, 'One or more species IDs not found.')


# DELETE Endpoint
@router.delete('/{id}', response={200: str})
def delete_recording_annotation(request: HttpRequest, id: int):
    try:
        annotation = RecordingAnnotation.objects.get(pk=id)

        # Check permission
        if annotation.recording.owner != request.user:
            raise HttpError(403, 'Permission denied.')

        annotation.delete()
        return 'Recording annotation deleted successfully.'
    except RecordingAnnotation.DoesNotExist:
        raise HttpError(404, 'Recording annotation not found.')
