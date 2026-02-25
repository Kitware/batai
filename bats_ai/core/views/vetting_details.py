from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from ninja import Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import VettingDetails

router = RouterPaginated()


class VettingDetailsSchema(Schema):
    id: int | None  # Allow null for cases where no details exist
    user_id: int
    reference_materials: str


class UpdateVettingDetailsSchema(Schema):
    reference_materials: str


@router.get("/user/{user_id}", response=VettingDetailsSchema)
def get_vetting_details_for_user(request: HttpRequest, user_id: int):
    if not (user_id == request.user.pk or request.user.is_superuser):
        # Don't leak user IDs, prefer to return a 404 over a 403
        raise Http404

    return get_object_or_404(VettingDetails, user_id=user_id)


@router.post("/user/{user_id}", response=VettingDetailsSchema)
def update_or_create_vetting_details_for_user(
    request: HttpRequest,
    payload: UpdateVettingDetailsSchema,
    user_id: int,
):
    if not (user_id == request.user.pk or request.user.is_superuser):
        raise Http404

    if len(payload.reference_materials) > 2000:
        return HttpResponseBadRequest(
            "reference_materials exceeds maximum length of 2000 characters"
        )

    vetting_details, _created = VettingDetails.objects.update_or_create(
        user_id=user_id,
        defaults={"reference_materials": payload.reference_materials},
    )
    return vetting_details
