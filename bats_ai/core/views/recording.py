from datetime import datetime
import json
import logging
from typing import Any

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import HttpRequest
from ninja import File, Form, Schema
from ninja.files import UploadedFile
from ninja.pagination import RouterPaginated

from bats_ai.core.models import (
    Annotations,
    CompressedSpectrogram,
    PulseMetadata,
    Recording,
    RecordingAnnotation,
    RecordingTag,
    SequenceAnnotations,
    Species,
)
from bats_ai.core.tasks.tasks import recording_compute_spectrogram
from bats_ai.core.views.recording_tag import RecordingTagSchema
from bats_ai.core.views.sequence_annotations import (
    SequenceAnnotationSchema,
    UpdateSequenceAnnotationSchema,
)
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
    tags: list[RecordingTagSchema] = []


class RecordingUploadSchema(Schema):
    name: str
    recorded_date: str
    recorded_time: str
    equipment: str | None = None
    comments: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    gridCellId: int | None = None
    publicVal: bool | None = None
    site_name: str | None = None
    software: str | None = None
    detector: str | None = None
    species_list: str | None = None
    unusual_occurrences: str | None = None
    tags: list[str] | None = None


class RecordingAnnotationSchema(Schema):
    species: list[SpeciesSchema] | None
    comments: str | None = None
    model: str | None = None
    owner: str
    confidence: float
    id: int | None = None
    hasDetails: bool
    submitted: bool

    @classmethod
    def from_orm(cls, obj: RecordingAnnotation, **kwargs):
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


class AnnotationSchema(Schema):
    start_time: int
    end_time: int
    low_freq: int
    high_freq: int
    species: list[SpeciesSchema]
    comments: str
    type: str | None = None
    id: int | None = None
    owner_email: str = None

    @classmethod
    def from_orm(cls, obj: Annotations, owner_email=None, **kwargs):
        return cls(
            start_time=obj.start_time,
            end_time=obj.end_time,
            low_freq=obj.low_freq,
            high_freq=obj.high_freq,
            species=[SpeciesSchema.from_orm(species) for species in obj.species.all()],
            comments=obj.comments,
            id=obj.id,
            type=obj.type,
            owner_email=owner_email,  # Include owner_email in the schema
        )


class UpdateAnnotationsSchema(Schema):
    start_time: int | None
    end_time: int | None
    low_freq: int | None
    high_freq: int | None
    species: list[SpeciesSchema] | None
    comments: str | None
    type: str | None
    id: int | None


class PulseMetadataSchema(Schema):
    id: int | None
    index: int
    bounding_box: Any
    contours: list

    @classmethod
    def from_orm(cls, obj: PulseMetadata):
        return cls(
            id=obj.id,
            index=obj.index,
            contours=obj.contours if obj.contours is not None else [],
            bounding_box=json.loads(obj.bounding_box.geojson),
        )


@router.post('/')
def create_recording(
    request: HttpRequest,
    payload: Form[RecordingUploadSchema],
    audio_file: File[UploadedFile],
    publicVal: bool = False,
):
    converted_date = datetime.strptime(payload.recorded_date, '%Y-%m-%d')
    converted_time = datetime.strptime(payload.recorded_time, '%H%M%S')
    point = None
    if payload.latitude and payload.longitude:
        point = Point(payload.longitude, payload.latitude)
    recording = Recording(
        name=payload.name,
        owner_id=request.user.pk,
        audio_file=audio_file,
        recorded_date=converted_date,
        recorded_time=converted_time,
        equipment=payload.equipment,
        grts_cell_id=payload.gridCellId,
        recording_location=point,
        public=publicVal,
        comments=payload.comments,
        detector=payload.detector,
        software=payload.software,
        site_name=payload.site_name,
        species_list=payload.species_list,
        unusual_occurrences=payload.unusual_occurrences,
    )
    recording.save()

    if payload.tags:
        for tag in payload.tags:
            tag, _ = RecordingTag.objects.get_or_create(user=request.user, text=tag)
            recording.tags.add(tag)

    recording.save()
    # Start generating recording as soon as created
    # this creates the spectrogram during the upload so it is available immediately afterwards
    # it will make the upload process longer but I think it's worth it.
    recording_compute_spectrogram.delay(recording.pk)
    return {'message': 'Recording updated successfully', 'id': recording.pk}


@router.patch('/{id}')
def update_recording(request: HttpRequest, id: int, recording_data: RecordingUploadSchema):
    try:
        recording = Recording.objects.get(pk=id, owner=request.user)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}

    if recording_data.name:
        recording.name = recording_data.name
    if recording_data.comments:
        recording.comments = recording_data.comments
    if recording_data.equipment:
        recording.equipment = recording_data.equipment
    if recording_data.recorded_date:
        converted_date = datetime.strptime(recording_data.recorded_date, '%Y-%m-%d')
        recording.recorded_date = converted_date
    if recording_data.recorded_time:
        converted_time = datetime.strptime(recording_data.recorded_time, '%H%M%S')
        recording.recorded_time = converted_time
    if recording_data.publicVal is not None and recording_data.publicVal != recording.public:
        recording.public = recording_data.publicVal
    if recording_data.latitude and recording_data.longitude:
        point = Point(recording_data.longitude, recording_data.latitude)
        recording.recording_location = point
    if recording_data.detector:
        recording.detector = recording_data.detector
    if recording_data.software:
        recording.software = recording_data.software
    if recording_data.site_name:
        recording.site_name = recording_data.site_name
    if recording_data.species_list:
        recording.species_list = recording_data.species_list
    if recording_data.unusual_occurrences:
        recording.unusual_occurrences = recording_data.unusual_occurrences
    if recording_data.tags:
        existing_tags = recording.tags.all()
        for tag in recording_data.tags:
            tag, _ = RecordingTag.objects.get_or_create(user=request.user, text=tag)
            if tag not in existing_tags:
                recording.tags.add(tag)
        # Remove any tags that are not in the updated list
        for existing_tag in existing_tags:
            if existing_tag.text not in recording_data.tags:
                recording.tags.remove(existing_tag)

    recording.save()

    return {'message': 'Recording updated successfully', 'id': recording.pk}


@router.delete('/{id}')
def delete_recording(
    request,
    id: int,
):
    try:
        recording = Recording.objects.get(pk=id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            # Delete the annotation
            recording.delete()
            return {'message': 'Recording deleted successfully'}
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}


@router.get('/')
def get_recordings(
    request: HttpRequest, public: bool | None = None, exclude_submitted: bool | None = None
):
    # Filter recordings based on the owner's id or public=True
    if public is not None and public:
        recordings = (
            Recording.objects.filter(public=True)
            .exclude(Q(owner=request.user) | Q(spectrogram__isnull=True))
            .annotate(tags_text=ArrayAgg('tags__text', filter=Q(tags__text__isnull=False)))
            .values()
        )
    else:
        recordings = (
            Recording.objects.filter(owner=request.user)
            .annotate(tags_text=ArrayAgg('tags__text', filter=Q(tags__text__isnull=False)))
            .values()
        )

    # TODO with larger dataset it may be better to do this in a queryset instead of python
    for recording in recordings:
        user = User.objects.get(id=recording['owner_id'])
        fileAnnotations = RecordingAnnotation.objects.filter(recording=recording['id'])
        recording['fileAnnotations'] = [
            RecordingAnnotationSchema.from_orm(fileAnnotation).dict()
            for fileAnnotation in fileAnnotations
        ]
        recording['owner_username'] = user.username
        recording['audio_file_presigned_url'] = default_storage.url(recording['audio_file'])
        recording['hasSpectrogram'] = Recording.objects.get(id=recording['id']).has_spectrogram
        if recording['recording_location']:
            recording['recording_location'] = json.loads(recording['recording_location'].json)
        unique_users_with_annotations = (
            Annotations.objects.filter(recording_id=recording['id'])
            .values('owner')
            .distinct()
            .count()
        )
        recording['userAnnotations'] = unique_users_with_annotations
        user_has_annotations = (
            Annotations.objects.filter(recording_id=recording['id'], owner=request.user).exists()
            or RecordingAnnotation.objects.filter(
                recording_id=recording['id'], owner=request.user
            ).exists()
        )
        recording['userMadeAnnotations'] = user_has_annotations

    if exclude_submitted:
        recordings = [
            recording
            for recording in recordings
            if not any(
                annotation['submitted'] and annotation['owner'] == request.user.username
                for annotation in recording['fileAnnotations']
            )
        ]

    return list(recordings)


@router.get('/{id}/')
def get_recording(request: HttpRequest, id: int):
    # Filter recordings based on the owner's id or public=True
    try:
        recordings = (
            Recording.objects.filter(pk=id)
            .annotate(tags_text=ArrayAgg('tags__text', filter=Q(tags__text__isnull=False)))
            .values()
        )
        if len(recordings) > 0:
            recording = recordings[0]

            user = User.objects.get(id=recording['owner_id'])
            recording['owner_username'] = user.username
            recording['audio_file_presigned_url'] = default_storage.url(recording['audio_file'])
            recording['hasSpectrogram'] = Recording.objects.get(id=recording['id']).has_spectrogram
            if recording['recording_location']:
                recording['recording_location'] = json.loads(recording['recording_location'].json)
            annotation_owners = (
                Annotations.objects.filter(recording_id=recording['id'])
                .values_list('owner', flat=True)
                .distinct()
            )
            recording_annotation_owners = (
                RecordingAnnotation.objects.filter(recording_id=recording['id'])
                .values_list('owner', flat=True)
                .distinct()
            )

            # Combine the sets of owners and count unique entries
            unique_users_with_annotations = len(
                set(annotation_owners).union(set(recording_annotation_owners))
            )
            recording['userAnnotations'] = unique_users_with_annotations
            user_has_annotations = (
                Annotations.objects.filter(
                    recording_id=recording['id'], owner=request.user
                ).exists()
                or RecordingAnnotation.objects.filter(
                    recording_id=recording['id'], owner=request.user
                ).exists()
            )
            recording['userMadeAnnotations'] = user_has_annotations
            fileAnnotations = RecordingAnnotation.objects.filter(recording=id).order_by(
                'confidence'
            )
            recording['fileAnnotations'] = [
                RecordingAnnotationSchema.from_orm(fileAnnotation).dict()
                for fileAnnotation in fileAnnotations
            ]
            return recording
        else:
            return {'error': 'Recording not found'}
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.get('/{recording_id}/recording-annotations')
def get_recording_annotations(request: HttpRequest, recording_id: int):
    fileAnnotations = RecordingAnnotation.objects.filter(recording=recording_id).order_by(
        'confidence'
    )
    output = [
        RecordingAnnotationSchema.from_orm(fileAnnotation).dict()
        for fileAnnotation in fileAnnotations
    ]
    return output


@router.get('/{id}/spectrogram')
def get_spectrogram(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}

    spectrogram = recording.spectrogram

    compressed = recording.compressed_spectrogram

    spectro_data = {
        'urls': spectrogram.image_url_list,
        'spectroInfo': {
            'spectroId': spectrogram.pk,
            'width': spectrogram.width,
            'height': spectrogram.height,
            'start_time': 0,
            'end_time': spectrogram.duration,
            'low_freq': spectrogram.frequency_min,
            'high_freq': spectrogram.frequency_max,
        },
    }
    if compressed:
        spectro_data['compressed'] = {
            'start_times': compressed.starts,
            'end_times': compressed.stops,
        }

    # Get distinct other users who have made annotations on the recording
    if recording.owner == request.user:
        other_users_qs = (
            Annotations.objects.filter(recording=recording)
            .exclude(owner=request.user)
            .values('owner__username', 'owner__email', 'owner__pk')
            .distinct()
        )

        other_users = [
            {
                'username': user['owner__username'],
                'email': user['owner__email'],
                'id': user['owner__pk'],
            }
            for user in other_users_qs
        ]

        spectro_data['otherUsers'] = other_users

    spectro_data['currentUser'] = request.user.email

    annotations_qs = Annotations.objects.filter(recording=recording, owner=request.user)
    sequence_annotations_qs = SequenceAnnotations.objects.filter(
        recording=recording, owner=request.user
    )

    # Serialize the annotations using AnnotationSchema
    annotations_data = [
        AnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
        for annotation in annotations_qs
    ]
    sequence_annotations_data = [
        SequenceAnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
        for annotation in sequence_annotations_qs
    ]

    spectro_data['annotations'] = annotations_data
    spectro_data['sequence'] = sequence_annotations_data
    return spectro_data


@router.get('/{id}/spectrogram/compressed')
def get_spectrogram_compressed(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)
        compressed_spectrogram = CompressedSpectrogram.objects.filter(recording=id).first()
    except compressed_spectrogram.DoesNotExist:
        return {'error': 'Compressed Spectrogram'}
    except recording.DoesNotExist:
        return {'error': 'Recording does not exist'}

    spectro_data = {
        'urls': compressed_spectrogram.image_url_list,
        'mask_urls': compressed_spectrogram.mask_url_list,
        'spectroInfo': {
            'spectroId': compressed_spectrogram.pk,
            'width': compressed_spectrogram.spectrogram.width,
            'start_time': 0,
            'end_time': compressed_spectrogram.spectrogram.duration,
            'height': compressed_spectrogram.spectrogram.height,
            'low_freq': compressed_spectrogram.spectrogram.frequency_min,
            'high_freq': compressed_spectrogram.spectrogram.frequency_max,
            'start_times': compressed_spectrogram.starts,
            'end_times': compressed_spectrogram.stops,
            'widths': compressed_spectrogram.widths,
            'compressedWidth': compressed_spectrogram.length,
        },
    }

    # Get distinct other users who have made annotations on the recording
    if recording.owner == request.user:
        other_users_qs = (
            Annotations.objects.filter(recording=recording)
            .exclude(owner=request.user)
            .values('owner__username', 'owner__email', 'owner__pk')
            .distinct()
        )

        other_users = [
            {
                'username': user['owner__username'],
                'email': user['owner__email'],
                'id': user['owner__pk'],
            }
            for user in other_users_qs
        ]

        spectro_data['otherUsers'] = other_users

    spectro_data['currentUser'] = request.user.email

    annotations_qs = Annotations.objects.filter(recording=recording, owner=request.user)
    sequence_annotations_qs = SequenceAnnotations.objects.filter(
        recording=recording, owner=request.user
    )

    # Serialize the annotations using AnnotationSchema
    annotations_data = [
        AnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
        for annotation in annotations_qs
    ]
    sequence_annotations_data = [
        SequenceAnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
        for annotation in sequence_annotations_qs
    ]

    spectro_data['annotations'] = annotations_data
    spectro_data['sequence'] = sequence_annotations_data
    return spectro_data


@router.get('/{id}/annotations')
def get_annotations(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            # Query annotations associated with the recording that are owned by the current user
            annotations_qs = Annotations.objects.filter(recording=recording, owner=request.user)

            # Serialize the annotations using AnnotationSchema
            annotations_data = [
                AnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
                for annotation in annotations_qs
            ]

            return annotations_data
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.get('/{id}/pulse_data')
def get_pulse_data(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)
        if recording.owner == request.user or recording.public:
            computed_pulse_annotation_qs = PulseMetadata.objects.filter(
                recording=recording
            ).order_by('index')
            return [
                PulseMetadataSchema.from_orm(pulse) for pulse in computed_pulse_annotation_qs.all()
            ]
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.get('/{id}/annotations/other_users')
def get_other_user_annotations(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            # Query annotations associated with the recording that are owned by other users
            annotations_qs = Annotations.objects.filter(recording=recording).exclude(
                owner=request.user
            )
            sequence_qs = SequenceAnnotations.objects.filter(recording=recording).exclude(
                owner=request.user
            )

            # Create a dictionary to store annotations for each user
            annotations_by_user = {}

            # Serialize the annotations using AnnotationSchema
            for annotation in annotations_qs:
                user_email = annotation.owner.email

                # If user_email is not already a key in the dictionary, initialize it with
                # an empty list
                annotations_by_user.setdefault(user_email, {'annotations': [], 'sequence': []})

                # Append the annotation to the list for the corresponding user_email
                annotations_by_user[user_email]['annotations'].append(
                    AnnotationSchema.from_orm(annotation, owner_email=user_email).dict()
                )

            for annotation in sequence_qs:
                user_email = annotation.owner.email

                # If user_email is not already a key in the dictionary, initialize it with
                # an empty list
                annotations_by_user.setdefault(user_email, {'annotations': [], 'sequence': []})

                # Append the annotation to the list for the corresponding user_email
                annotations_by_user[user_email]['sequence'].append(
                    SequenceAnnotationSchema.from_orm(annotation, owner_email=user_email).dict()
                )

            return annotations_by_user
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.get('/{id}/annotations/user/{userId}')
def get_user_annotations(request: HttpRequest, id: int, userId: int):
    try:
        recording = Recording.objects.get(pk=id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            # Query annotations associated with the recording that are owned by the current user
            annotations_qs = Annotations.objects.filter(recording=recording, owner=userId)

            # Serialize the annotations using AnnotationSchema
            annotations_data = [
                AnnotationSchema.from_orm(annotation).dict() for annotation in annotations_qs
            ]

            return annotations_data
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.put('/{id}/annotations')
def put_annotation(
    request,
    id: int,
    annotation: AnnotationSchema,
    species_ids: list[int],
):
    try:
        recording = Recording.objects.get(pk=id)
        if recording.owner == request.user or recording.public:
            # Create a new annotation
            new_annotation = Annotations.objects.create(
                recording=recording,
                owner=request.user,
                start_time=annotation.start_time,
                end_time=annotation.end_time,
                low_freq=annotation.low_freq,
                high_freq=annotation.high_freq,
                comments=annotation.comments,
                type=annotation.type,
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
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.patch('/{recording_id}/annotations/{id}')
def patch_annotation(
    request,
    recording_id: int,
    id: int,
    annotation: UpdateAnnotationsSchema,
    species_ids: list[int] | None,
):
    try:
        recording = Recording.objects.get(pk=recording_id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            annotation_instance = Annotations.objects.get(
                pk=id, recording=recording, owner=request.user
            )

            # Update annotation details
            if annotation.start_time is not None:
                annotation_instance.start_time = annotation.start_time
            if annotation.end_time:
                annotation_instance.end_time = annotation.end_time
            if annotation.low_freq:
                annotation_instance.low_freq = annotation.low_freq
            if annotation.high_freq:
                annotation_instance.high_freq = annotation.high_freq
            if annotation.type:
                annotation_instance.type = annotation.type
            else:
                annotation_instance.type = None
            if annotation.comments:
                annotation_instance.comments = annotation.comments
            annotation_instance.save()

            # Clear existing species associations
            if species_ids is not None:
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
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}


@router.patch('/{recording_id}/sequence-annotations/{id}')
def patch_sequence_annotation(
    request,
    recording_id: int,
    id: int,
    annotation: UpdateSequenceAnnotationSchema,
    species_ids: list[int] | None,
):
    try:
        recording = Recording.objects.get(pk=recording_id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            annotation_instance = SequenceAnnotations.objects.get(
                pk=id, recording=recording, owner=request.user
            )

            # Update annotation details
            if annotation.start_time is not None:
                annotation_instance.start_time = annotation.start_time
            if annotation.end_time:
                annotation_instance.end_time = annotation.end_time
            if annotation.comments:
                annotation_instance.comments = annotation.comments
            if annotation.type:
                annotation_instance.type = annotation.type
            else:
                annotation_instance.type = None
            annotation_instance.save()

            # Clear existing species associations
            if species_ids is not None:
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
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}


@router.delete('/{recording_id}/annotations/{id}')
def delete_annotation(request, recording_id: int, id: int):
    try:
        recording = Recording.objects.get(pk=recording_id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            annotation_instance = Annotations.objects.get(
                pk=id, recording=recording, owner=request.user
            )

            # Delete the annotation
            annotation_instance.delete()

            return {'message': 'Annotation deleted successfully'}
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}


# SEQUENCE ANNOTATIONS


@router.get('/{id}/sequence-annotations')
def get_sequence_annotations(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            # Query annotations associated with the recording that are owned by the current user
            annotations_qs = SequenceAnnotations.objects.filter(
                recording=recording, owner=request.user
            )

            # Serialize the annotations using AnnotationSchema
            annotations_data = [
                SequenceAnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
                for annotation in annotations_qs
            ]

            return annotations_data
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.put('/{id}/sequence-annotations')
def put_sequence_annotation(
    request,
    id: int,
    annotation: SequenceAnnotationSchema,
    species_ids: list[int] | None,
):
    try:
        recording = Recording.objects.get(pk=id)
        if recording.owner == request.user or recording.public:
            # Create a new annotation
            new_annotation = SequenceAnnotations.objects.create(
                recording=recording,
                owner=request.user,
                start_time=annotation.start_time,
                end_time=annotation.end_time,
                type=annotation.type,
                comments=annotation.comments,
            )

            return {'message': 'Annotation added successfully', 'id': new_annotation.pk}
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}


@router.delete('/{recording_id}/sequence-annotations/{id}')
def delete_sequence_annotation(request, recording_id: int, id: int):
    try:
        recording = Recording.objects.get(pk=recording_id)

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            annotation_instance = SequenceAnnotations.objects.get(
                pk=id, recording=recording, owner=request.user
            )

            # Delete the annotation
            annotation_instance.delete()

            return {'message': 'Annotation deleted successfully'}
        else:
            return {
                'error': 'Permission denied. You do not own this recording, and it is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
    except Annotations.DoesNotExist:
        return {'error': 'Annotation not found'}
