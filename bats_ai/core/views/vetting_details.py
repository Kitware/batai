from django.http import Http404, HttpRequest, HttpResponseBadRequest
from ninja import Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import VettingDetails

router = RouterPaginated()


class VettingDetailsSchema(Schema):
    id: int | None  # Allow null for cases where no details exist
    user_id: int
    reference_materials: str

    @classmethod
    def from_orm(cls, obj):
        return cls(id=obj.id, reference_materials=obj.reference_materials, user_id=obj.user_id)


class UpdateVettingDetailsSchema(Schema):
    reference_materials: str


@router.get('/user/{user_id}', response=VettingDetailsSchema)
def get_vetting_details_for_user(request: HttpRequest, user_id: int):
    details = VettingDetails.objects.filter(user_id=user_id).first()

    if not details:  # Ensure we return a consistent schema even if no details exist
        return {'id': None, 'user_id': user_id, 'reference_materials': ''}

    if details.user != request.user and not request.user.is_staff:
        # Don't leak user IDs, prefer to return a 404 over a 403
        raise Http404

    return details


@router.post('/user/{user_id}', response=VettingDetailsSchema)
def update_or_create_vetting_details_for_user(
    request: HttpRequest,
    payload: UpdateVettingDetailsSchema,
    user_id: int,
):
    if not (request.user.pk == user_id or request.user.is_staff):
        raise Http404

    if len(payload.reference_materials) > 2000:
        return HttpResponseBadRequest(
            'reference_materials exceeds maximum length of 2000 characters'
        )

    details = VettingDetails.objects.filter(user_id=user_id).first()

    if not details:
        details = VettingDetails(user=request.user, reference_materials=payload.reference_materials)
    else:
        details.reference_materials = payload.reference_materials

    details.save()

    return details
