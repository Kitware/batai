import logging

from django.http import HttpRequest
from ninja import Schema
from ninja.errors import HttpError
from ninja.pagination import RouterPaginated
from oauth2_provider.models import AccessToken

logger = logging.getLogger(__name__)


router = RouterPaginated()


class AnnotationSchema(Schema):
    recording: int  # Foreign Key to index
    owner_username: str
    start_time: int
    end_time: int
    low_freq: int
    high_freq: int
    species: list[int]
    comments: str


def get_owner_id(request: HttpRequest):
    token = request.headers.get('Authorization').replace('Bearer ', '')
    token_found = AccessToken.objects.get(token=token)
    if not token_found:
        raise HttpError(401, 'Authentication credentials were not provided.')

    return token_found.user.pk
