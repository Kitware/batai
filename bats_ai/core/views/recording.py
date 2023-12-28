import json
import sys
import tempfile
from datetime import datetime

from ninja import Field, FilterSchema, Query, Router, Schema

from ninja.errors import HttpError
from ninja.security import HttpBearer

from pydantic import UUID4
from django.core.files.storage import default_storage
from django.contrib.auth.models import User

from django.conf import settings
from django.contrib.gis.db.models.aggregates import Collect
from django.contrib.gis.db.models.functions import Transform
from django.contrib.postgres.aggregates import JSONBAgg
from django.core.paginator import Paginator
from django.db import transaction
from ninja.pagination import RouterPaginated
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import JSONObject  # type: ignore
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from bats_ai.core.models import Recording
from oauth2_provider.models import AccessToken

import logging

logger = logging.getLogger(__name__)


router = RouterPaginated()


class RecordingSchema(Schema):
    name: str
    audio_file: str
    owner: int
    recorded_date: str
    equipment: str
    comments: str
    recording_location: str
    grts_cell_id: int
    grts_cell: int




@router.put("/")
def update_recording(request: HttpRequest, payload: RecordingSchema):
    recording = Recording(
        name=payload.name,
        owner_id=request.user.id,
        audio_file=payload.audio_file,
        equipment=payload.equipment,
        comments=payload.comments,
    )
    recording.save()

    return {"message": "Recording updated successfully", "data": RecordingSchema.from_orm(recording)}

@router.get('/')
def get_recordings(request: HttpRequest):
    # Check if the user is authenticated and get userId
    token = request.headers.get('Authorization').replace('Bearer ', '')
    token_found = AccessToken.objects.get(token=token)
    logger.warning(token_found.user.pk)
    if not token_found:
        raise HttpError(401, 'Authentication credentials were not provided.')

    # Filter recordings based on the owner's id
    recordings = Recording.objects.filter(owner=token_found.user.pk).values()

    for recording in recordings:
        user = User.objects.get(id=recording['owner_id'])
        recording['owner_username'] = user.username
        recording['audio_file_presigned_url'] = default_storage.url(recording['audio_file'])

    # Return the serialized data
    return list(recordings)