import logging

from ninja import NinjaAPI
from ninja.security import HttpBearer
from oauth2_provider.models import AccessToken

from bats_ai.core.views import RecordingRouter, SpeciesRouter

logger = logging.getLogger(__name__)


class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        logger.warning(f'Checking Token: {token}')
        print(token)
        logger.warning(AccessToken.objects.get(token=token))
        if AccessToken.objects.get(token=token):
            logger.warning('returning token')
            return token


api = NinjaAPI()

api.add_router('/recording/', RecordingRouter)
api.add_router('/species/', SpeciesRouter)
