from __future__ import annotations

from django.http import Http404, HttpRequest
from ninja import Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import RecordingTag


class RecordingTagSchema(Schema):
    text: str
    user: int


router = RouterPaginated()


@router.get("/")
def get_recording_tags(request: HttpRequest):
    user = request.user
    if not user:
        return Http404()
    return list(RecordingTag.objects.filter(user=request.user).values())
