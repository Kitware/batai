from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from ninja import Field, ModelSchema, Router, Schema
from ninja.errors import AuthorizationError

from bats_ai.core.models import Annotations, SequenceAnnotations
from bats_ai.core.views.species import SpeciesSchema

if TYPE_CHECKING:
    from django.http import HttpRequest

router = Router()


class SequenceAnnotationSchema(ModelSchema):
    class Meta:
        model = SequenceAnnotations
        fields = ["id", "start_time", "end_time", "type", "comments"]

    species: list[SpeciesSchema] | None
    owner_email: str | None = Field(None, alias="owner.email")


class UpdateSequenceAnnotationSchema(Schema):
    start_time: int = None
    end_time: int = None
    type: str | None = None
    comments: str | None = None


@router.get("/{pk}", response=list[SequenceAnnotationSchema])
def get_sequence_annotation(request: HttpRequest, pk: int):
    annotation = get_object_or_404(Annotations.objects.select_related("recording"), pk=pk)
    recording = annotation.recording

    # Check if the user owns the recording or if the recording is public
    if not (recording.owner == request.user or recording.public):
        raise AuthorizationError

    # Query annotations associated with the recording that are owned by the current user
    return (
        SequenceAnnotations.objects.filter(recording=recording, owner=request.user)
        .select_related("owner")
        .prefetch_related("species")
    )
