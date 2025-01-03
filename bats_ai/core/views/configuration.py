import logging

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from ninja import Schema
from ninja.pagination import RouterPaginated

from bats_ai.core.models import Configuration

logger = logging.getLogger(__name__)


router = RouterPaginated()


# Define schema for the Configuration data
class ConfigurationSchema(Schema):
    display_pulse_annotations: bool
    display_sequence_annotations: bool


# Helper function to check admin user
def is_admin(user):
    return user.is_superuser


# Endpoint to retrieve the configuration status
@router.get('/', response=ConfigurationSchema)
def get_configuration(request):
    config = Configuration.objects.first()
    if not config:
        return JsonResponse({'error': 'No configuration found'}, status=404)
    return ConfigurationSchema.from_orm(config)


# Endpoint to update the configuration (admin only)
@router.patch('/')
@method_decorator(user_passes_test(is_admin), name='dispatch')
def update_configuration(request, payload: ConfigurationSchema):
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
