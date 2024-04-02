from datetime import datetime

from django.http import HttpRequest, JsonResponse
from guano import GuanoFile
from ninja import File, Schema
from ninja.files import UploadedFile
from ninja.pagination import RouterPaginated

router = RouterPaginated()


class GuanoMetadataSchema(Schema):
    nabat_grid_cell_grts_id: str
    nabat_latitude: float
    nabat_longitude: float
    nabat_site_name: str
    nabat_activation_start_time: datetime
    nabat_activation_end_time: datetime
    nabat_software_type: str
    nabat_species_list: list[str]
    nabat_comments: str
    nabat_detector_type: str
    nabat_unusual_occurrences: str


router = RouterPaginated()


@router.post('/')
def default_data(
    request: HttpRequest,
    audio_file: File[UploadedFile],
):
    try:
        # Read GUANO metadata from the file name provided
        gfile = GuanoFile(audio_file.file.name)

        # Extract required NABat fields
        nabat_fields = {
            'nabat_grid_cell_grts_id': gfile.get('NABat|Grid Cell GRTS ID', ''),
            'nabat_latitude': float(gfile.get('NABat|Latitude', 0)),
            'nabat_longitude': float(gfile.get('NABat|Longitude', 0)),
            'nabat_site_name': gfile.get('NABat|Site Name', ''),
        }

        # Extract additional fields with conditionals
        additional_fields = {
            'nabat_activation_start_time': datetime.strptime(
                gfile.get('NABat|Activation start time', ''), '%Y%m%dT%H%M%S'
            )
            if 'NABat|Activation start time' in gfile
            else None,
            'nabat_activation_end_time': datetime.strptime(
                gfile.get('NABat|Activation end time', ''), '%Y%m%dT%H%M%S'
            )
            if 'NABat|Activation end time' in gfile
            else None,
            'nabat_software_type': gfile.get('NABat|Software type', ''),
            'nabat_species_list': gfile.get('NABat|Species List', '').split(','),
            'nabat_comments': gfile.get('NABat|Comments', ''),
            'nabat_detector_type': gfile.get('NABat|Detector type', ''),
            'nabat_unusual_occurrences': gfile.get('NABat|Unusual occurrences', ''),
        }

        # Combine all extracted fields
        metadata = {**nabat_fields, **additional_fields}

        return JsonResponse(metadata, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
