from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from typing import TYPE_CHECKING

from django.http import HttpRequest, JsonResponse
from ninja import File, Schema

# Django-Ninja accesses additional params directly, so we need to ignore the type checker.
from ninja.files import UploadedFile  # noqa: TC002
from ninja.pagination import RouterPaginated

from bats_ai.core.utils.guano_utils import extract_guano_metadata

if TYPE_CHECKING:
    from datetime import datetime


router = RouterPaginated()
logger = logging.getLogger(__name__)


class GuanoMetadataSchema(Schema):
    nabat_grid_cell_grts_id: str | None = None
    nabat_sample_frame_id: int | None = None
    nabat_latitude: float | None = None
    nabat_longitude: float | None = None
    nabat_site_name: str | None = None
    nabat_activation_start_time: datetime | None = None
    nabat_activation_end_time: datetime | None = None
    nabat_software_type: str | None = None
    nabat_species_list: list[str] | None = None
    nabat_comments: str | None = None
    nabat_detector_type: str | None = None
    nabat_unusual_occurrences: str | None = None


router = RouterPaginated()


def _write_uploaded_audio_to_temp_file(audio_file: UploadedFile) -> str:
    """Persist uploaded audio to a real filesystem path for GUANO parsing."""
    suffix = os.path.splitext(audio_file.name or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        for chunk in audio_file.chunks():
            temp_file.write(chunk)
        return temp_file.name


@router.post("/")
def default_data(
    request: HttpRequest,
    audio_file: File[UploadedFile],
):
    temp_path: str | None = None
    try:
        # Uploaded files may be in-memory or have a non-filesystem name. Write to a
        # temporary file so guano reads the same way as local script usage.
        temp_path = _write_uploaded_audio_to_temp_file(audio_file)
        metadata = extract_guano_metadata(
            temp_path,
            check_filename=True,
            filename=audio_file.name,
        )
        return JsonResponse(metadata, safe=False)

    except Exception as e:
        logger.exception("Error extracting GUANO metadata", exc_info=e)
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if temp_path:
            with contextlib.suppress(FileNotFoundError):
                os.remove(temp_path)
