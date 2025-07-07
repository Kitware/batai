from datetime import datetime
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from pydantic import BaseModel, ConfigDict

from bats_ai.core.models import ExportedAnnotationFile

logger = logging.getLogger(__name__)

router = Router()


class ExportedAnnotationFileSchema(BaseModel):
    id: int
    status: str
    downloadUrl: str | None
    created: datetime
    expiresAt: datetime | None

    model_config = ConfigDict(from_attributes=True)


@router.get('/', response=list[ExportedAnnotationFileSchema])
def list_exports(request):
    exports = ExportedAnnotationFile.objects.order_by('-created')
    return [
        ExportedAnnotationFileSchema(
            id=e.id,
            status=e.status,
            downloadUrl=e.download_url if e.status == 'complete' else None,
            created=e.created,
            expiresAt=e.expires_at,
        )
        for e in exports
    ]


@router.get('/{export_id}', response=ExportedAnnotationFileSchema)
def get_export_status(request, export_id: int):
    export = get_object_or_404(ExportedAnnotationFile, pk=export_id)
    return ExportedAnnotationFileSchema(
        id=export.id,
        status=export.status,
        downloadUrl=export.download_url if export.status == 'complete' else None,
        created=export.created,
        expiresAt=export.expires_at,
    )


@router.delete('/{export_id}')
def delete_export(request, export_id: int):
    export = get_object_or_404(ExportedAnnotationFile, pk=export_id)

    # Optional: block deleting exports still in progress
    if export.status not in ('complete', 'failed', 'expired'):
        return JsonResponse(
            {'error': 'Cannot delete an export that is still in progress.'},
            status=400,
        )

    export.delete()
    return JsonResponse({'success': True})
