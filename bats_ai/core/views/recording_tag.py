from __future__ import annotations

from django.db.models import Q
from django.http import Http404, HttpRequest
from ninja import Schema
from ninja.pagination import Router

from bats_ai.core.models import RecordingTag


class RecordingTagSchema(Schema):
    text: str
    user: int


router = Router()


@router.get("/", response=list[str])
def get_recording_tags(request: HttpRequest):
    if not request.user:
        return Http404()
    # User's own tags + tags on public recordings (so non-admins get suggestions when filtering shared list).
    return list(
        RecordingTag.objects.filter(
            Q(user=request.user) | Q(recording__public=True)
        )
        .values_list("text", flat=True)
        .distinct()
    )
