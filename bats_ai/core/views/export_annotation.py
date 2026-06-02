from __future__ import annotations

from datetime import datetime
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from ninja import Router
from pydantic import BaseModel, ConfigDict

from bats_ai.core.models import ExportedAnnotationFile

logger = logging.getLogger(__name__)

router = Router()


def _is_tag_annotation_summary_export(export: ExportedAnnotationFile) -> bool:
    filters_applied = export.filters_applied
    return (
        isinstance(filters_applied, dict)
        and filters_applied.get("type") == "tag_annotation_summary"
    )


def _is_recording_annotation_hierarchy_export(
    export: ExportedAnnotationFile,
) -> bool:
    filters_applied = export.filters_applied
    return (
        isinstance(filters_applied, dict)
        and filters_applied.get("type") == "recording_annotation_hierarchy"
    )


def _can_access_export(request, export: ExportedAnnotationFile) -> bool:
    # Tag annotation summary exports include user-level aggregate stats,
    # so only admins can access them.
    if _is_tag_annotation_summary_export(export) or _is_recording_annotation_hierarchy_export(
        export
    ):
        return request.user.is_authenticated and request.user.is_superuser
    return True


class ExportedAnnotationFileSchema(BaseModel):
    id: int
    status: str
    downloadUrl: str | None
    created: datetime
    expiresAt: datetime | None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response=list[ExportedAnnotationFileSchema])
def list_exports(request):
    exports = ExportedAnnotationFile.objects.order_by("-created")
    return [
        ExportedAnnotationFileSchema(
            id=e.id,
            status=e.status,
            downloadUrl=e.download_url if e.status == "complete" else None,
            created=e.created,
            expiresAt=e.expires_at,
        )
        for e in exports
        if _can_access_export(request, e)
    ]


@router.get("/{export_id}", response=ExportedAnnotationFileSchema)
def get_export_status(request, export_id: int):
    export = get_object_or_404(ExportedAnnotationFile, pk=export_id)
    if not _can_access_export(request, export):
        return JsonResponse({"error": "Permission denied"}, status=403)
    return ExportedAnnotationFileSchema(
        id=export.id,
        status=export.status,
        downloadUrl=(export.download_url if export.status == "complete" else None),
        created=export.created,
        expiresAt=export.expires_at,
    )


@router.delete("/{export_id}")
def delete_export(request, export_id: int):
    export = get_object_or_404(ExportedAnnotationFile, pk=export_id)
    if not _can_access_export(request, export):
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Optional: block deleting exports still in progress
    if export.status not in ("complete", "failed", "expired"):
        return JsonResponse(
            {"error": "Cannot delete an export that is still in progress."},
            status=400,
        )

    export.delete()
    return JsonResponse({"success": True})
