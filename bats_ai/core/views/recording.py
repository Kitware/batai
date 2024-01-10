from datetime import datetime
import logging

from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.http import HttpRequest
from ninja import File, Form, Schema
from ninja.files import UploadedFile
from ninja.pagination import RouterPaginated

from bats_ai.core.models import Annotations, Recording, Species
from bats_ai.core.views.species import SpeciesSchema

logger = logging.getLogger(__name__)


router = RouterPaginated()


class RecordingSchema(Schema):
    name: str
    audio_file: str
    owner: int
    recorded_date: str | None
    equipment: str
    comments: str
    recording_location: str | None
    grts_cell_id: int | None
    grts_cell: int | None


class RecordingUploadSchema(Schema):
    name: str
    recorded_date: str
    equipment: str | None
    comments: str | None


class AnnotationSchema(Schema):
    start_time: int
    end_time: int
    low_freq: int
    high_freq: int
    species: list[SpeciesSchema]
    comments: str
    id: int


class UpdateAnnotationsSchema(Schema):
    start_time: int | None
    end_time: int | None
    low_freq: int | None
    high_freq: int | None
    species: list[SpeciesSchema] | None
    comments: str | None
    id: int | None


def get_user(request: HttpRequest):
    auth_header = request.headers.get('Authorization', None)
    if auth_header is not None:
        token = request.headers.get('Authorization').replace('Bearer ', '')
        token_found = AccessToken.objects.get(token=token)
        if not token_found:
            raise HttpError(401, 'Authentication credentials were not provided.')
        return token_found.user
    elif request.user:
        logger.warning(f'User: {request.user}')
        return request.user


@router.post('/')
def create_recording(
    request: HttpRequest, payload: Form[RecordingUploadSchema], audio_file: File[UploadedFile]
):
    converted_date = datetime.strptime(payload.recorded_date, '%Y-%m-%d')
    recording = Recording(
        name=payload.name,
        owner_id=request.user.pk,
        audio_file=audio_file,
        recorded_date=converted_date,
        equipment=payload.equipment,
        comments=payload.comments,
    )
    recording.save()

    return {'message': 'Recording updated successfully', 'id': recording.pk}


@router.get('/')
def get_recordings(request: HttpRequest):
    # Filter recordings based on the owner's id
    recordings = Recording.objects.filter(owner=request.user).values()

    for recording in recordings:
        user = User.objects.get(id=recording['owner_id'])
        recording['owner_username'] = user.username
        recording['audio_file_presigned_url'] = default_storage.url(recording['audio_file'])

    # Return the serialized data
    return list(recordings)


@router.get('/{id}/spectrogram')
def get_spectrogram(request: HttpRequest, id: int):
    user_id = get_user(request)
    try:
        recording = Recording.objects.get(pk=id)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}

    spectro_data = recording.generate_spectrogram()

    annotations_qs = Annotations.objects.filter(recording=recording, owner=user_id)

    # Serialize the annotations using AnnotationSchema
    annotations_data = [
        AnnotationSchema.from_orm(annotation).dict() for annotation in annotations_qs
    ]
    spectro_data['annotations'] = annotations_data
    return spectro_data


@router.get('/{id}/annotations')
def get_annotations(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id, owner=request.user)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}

    # Query annotations associated with the recording
    annotations_qs = Annotations.objects.filter(recording=recording, owner=user_id)

    # Serialize the annotations using AnnotationSchema
    annotations_data = [
        AnnotationSchema.from_orm(annotation).dict() for annotation in annotations_qs
    ]

    return annotations_data


@router.put('/{id}/annotations')
def put_annotation(
    request,
    id: int,
    annotation: AnnotationSchema,
    species_ids: list[int],
):
    try:
        recording = Recording.objects.get(pk=id, owner=request.user)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}

    # Create a new annotation
    new_annotation = Annotations.objects.create(
        recording=recording,
        owner=request.user,
        start_time=annotation.start_time,
        end_time=annotation.end_time,
        low_freq=annotation.low_freq,
        high_freq=annotation.high_freq,
        comments=annotation.comments,
    )

    # Add species to the annotation based on the provided species_ids
    for species_id in species_ids:
        try:
            species_obj = Species.objects.get(pk=species_id)
            new_annotation.species.add(species_obj)
        except Species.DoesNotExist:
            # Handle the case where the species with the given ID doesn't exist
            return {'error': f'Species with ID {species_id} not found'}

    return {'message': 'Annotation added successfully', 'id': new_annotation.pk}


@router.patch('/{recording_id}/annotations/{id}')
def patch_annotation(
    request,
    recording_id: int,
    id: int,
    annotation: UpdateAnnotationsSchema,
    species_ids: list[int],
):
    try:
        recording = Recording.objects.get(pk=recording_id, owner=request.user)
        annotation_instance = Annotations.objects.get(pk=id, recording=recording)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}

    # Update annotation details
    if annotation.start_time:
        annotation_instance.start_time = annotation.start_time
    if annotation.end_time:
        annotation_instance.end_time = annotation.end_time
    if annotation.low_freq:
        annotation_instance.low_freq = annotation.low_freq
    if annotation.high_freq:
        annotation_instance.high_freq = annotation.high_freq
    if annotation.comments:
        annotation_instance.comments = annotation.comments
    annotation_instance.save()

    # Clear existing species associations
    annotation_instance.species.clear()

    # Add species to the annotation based on the provided species_ids
    for species_id in species_ids:
        try:
            species_obj = Species.objects.get(pk=species_id)
            annotation_instance.species.add(species_obj)
        except Species.DoesNotExist:
            # Handle the case where the species with the given ID doesn't exist
            return {'error': f'Species with ID {species_id} not found'}

    return {'message': 'Annotation updated successfully', 'id': annotation_instance.pk}


@router.delete('/{recording_id}/annotations/{id}')
def delete_annotation(request, recording_id: int, id: int):
    try:
        recording = Recording.objects.get(pk=recording_id, owner=request.user)
        annotation_instance = Annotations.objects.get(pk=id, recording=recording)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}

    # Delete the annotation
    annotation_instance.delete()

    return {'message': 'Annotation deleted successfully'}
