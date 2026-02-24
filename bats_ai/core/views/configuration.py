from __future__ import annotations

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
    default_color_scheme: Configuration.AvailableColorScheme
    default_spectrogram_background_color: str
    non_admin_upload_enabled: bool
    mark_annotations_completed_enabled: bool


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
        default_color_scheme=config.default_color_scheme,
        default_spectrogram_background_color=config.default_spectrogram_background_color,
        non_admin_upload_enabled=config.non_admin_upload_enabled,
        mark_annotations_completed_enabled=config.mark_annotations_completed_enabled,
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


@router.get('/me')
def get_current_user(request):
    if request.user.is_authenticated:
        return {
            'email': request.user.email,
            'name': request.user.username,
            'id': request.user.id,
        }
    return {'email': '', 'name': ''}
