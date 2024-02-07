from django.http import HttpRequest
from ninja import Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import Annotations, Recording, TemporalAnnotations

router = RouterPaginated()


class TemporalAnnotationSchema(Schema):
    start_time: int
    end_time: int
    type: str
    comments: str
    owner_email: str = None

    @classmethod
    def from_orm(cls, obj, owner_email=None, **kwargs):
        return cls(
            start_time=obj.start_time,
            end_time=obj.end_time,
            type=obj.type,
            comments=obj.comments,
            id=obj.id,
            owner_email=owner_email,  # Include owner_email in the schema
        )


@router.get('/{id}')
def get_temporal_annotation(request: HttpRequest, id: int):
    try:
        annotation = Annotations.objects.get(pk=id)
        recording = annotation.recording

        # Check if the user owns the recording or if the recording is public
        if recording.owner == request.user or recording.public:
            # Query annotations associated with the recording that are owned by the current user
            annotations_qs = TemporalAnnotations.objects.filter(
                recording=recording, owner=request.user
            )

            # Serialize the annotations using AnnotationSchema
            annotations_data = [
                TemporalAnnotationSchema.from_orm(annotation, owner_email=request.user.email).dict()
                for annotation in annotations_qs
            ]

            return annotations_data
        else:
            return {
                'error': 'Permission denied. You do not own this annotation, or the associated recording is not public.'
            }

    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}
