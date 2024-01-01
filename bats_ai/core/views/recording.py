import logging
from datetime import datetime 
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.http import HttpRequest
from ninja import File, Form, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import RouterPaginated
from oauth2_provider.models import AccessToken

from bats_ai.core.models import Recording

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


def get_owner_id(request: HttpRequest):
    token = request.headers.get('Authorization').replace('Bearer ', '')
    token_found = AccessToken.objects.get(token=token)
    if not token_found:
        raise HttpError(401, 'Authentication credentials were not provided.')

    return token_found.user.pk


@router.post('/')
def create_recording(
    request: HttpRequest, payload: Form[RecordingUploadSchema], audio_file: File[UploadedFile]
):
    user_id = get_owner_id(request)
    converted_date = datetime.strptime(payload.recorded_date, "%Y-%m-%d")
    recording = Recording(
        name=payload.name,
        owner_id=user_id,
        audio_file=audio_file,
        recorded_date=converted_date,
        equipment=payload.equipment,
        comments=payload.comments,
    )
    recording.save()

    return {'message': 'Recording updated successfully', 'id': recording.pk}


@router.get('/')
def get_recordings(request: HttpRequest):
    # Check if the user is authenticated and get userId
    user_id = get_owner_id(request)

    # Filter recordings based on the owner's id
    recordings = Recording.objects.filter(owner=user_id).values()

    for recording in recordings:
        user = User.objects.get(id=recording['owner_id'])
        recording['owner_username'] = user.username
        recording['audio_file_presigned_url'] = default_storage.url(recording['audio_file'])

    # Return the serialized data
    return list(recordings)


@router.get('/{id}/spectrogram')
def get_spectrogram(request: HttpRequest, id: int):
    try:
        recording = Recording.objects.get(pk=id)
    except Recording.DoesNotExist:
        return {'error': 'Recording not found'}

    base64_spectrogram = recording.generate_spectrogram()

    return {'base64_spectrogram': base64_spectrogram}

