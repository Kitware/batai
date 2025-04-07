import logging

from django.http import JsonResponse
from ninja import Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import Configuration

logger = logging.getLogger(__name__)


router = RouterPaginated()


# Define schema for the Configuration data
class ConfigurationSchema(Schema):
    display_pulse_annotations: bool
    display_sequence_annotations: bool
    is_admin: bool | None = None
    run_inference_on_upload: bool
    spectrogram_x_stretch: float
    spectrogram_view: Configuration.SpectrogramViewMode


# Endpoint to retrieve the configuration status
@router.get('/', response=ConfigurationSchema)
def get_configuration(request):
    config = Configuration.objects.first()
    if not config:
        return JsonResponse({'error': 'No configuration found'}, status=404)
    return ConfigurationSchema(
        display_pulse_annotations=config.display_pulse_annotations,
        display_sequence_annotations=config.display_sequence_annotations,
        run_inference_on_upload=config.run_inference_on_upload,
        spectrogram_x_stretch=config.spectrogram_x_stretch,
        spectrogram_view=config.spectrogram_view,
        is_admin=request.user.is_authenticated and request.user.is_superuser,
    )


# Endpoint to update the configuration (admin only)
@router.patch('/')
def update_configuration(request, payload: ConfigurationSchema):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    config = Configuration.objects.first()
    if not config:
        return JsonResponse({'error': 'No configuration found'}, status=404)
    for attr, value in payload.dict().items():
        setattr(config, attr, value)
    config.save()
    return ConfigurationSchema.from_orm(config)


@router.get('/is_admin/')
def check_is_admin(request):
    if request.user.is_authenticated:
        return {'is_admin': request.user.is_superuser}
    return {'is_admin': False}
