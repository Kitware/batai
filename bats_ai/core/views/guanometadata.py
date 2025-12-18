from datetime import datetime
import logging

from django.http import HttpRequest, JsonResponse
from ninja import File, Schema
from ninja.files import UploadedFile
from ninja.pagination import RouterPaginated

from bats_ai.core.utils.guano_utils import extract_guano_metadata

router = RouterPaginated()
logger = logging.getLogger(__name__)


class GuanoMetadataSchema(Schema):
    nabat_grid_cell_grts_id: str | None = None
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


@router.post('/')
def default_data(
    request: HttpRequest,
    audio_file: File[UploadedFile],
):
    try:
        # Extract GUANO metadata using utility function
        metadata = extract_guano_metadata(audio_file.file.name)
        return JsonResponse(metadata, safe=False)

    except Exception as e:
        logger.exception('Error extracting GUANO metadata', exc_info=e)
        return JsonResponse({'error': str(e)}, status=500)
