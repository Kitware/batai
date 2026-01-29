import logging

from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.security import HttpBearer
from oauth2_provider.models import AccessToken
from oauth2_provider.oauth2_backends import get_oauthlib_core

from bats_ai.core.views import (
    ConfigurationRouter,
    ExportAnnotationRouter,
    GRTSCellsRouter,
    GuanoMetadataRouter,
    ProcessingTaskRouter,
    RecordingAnnotationRouter,
    RecordingRouter,
    RecordingTagRouter,
    SpeciesRouter,
    VettingRouter,
)
from bats_ai.core.views.nabat import NABatConfigurationRouter, NABatRecordingRouter

logger = logging.getLogger(__name__)


class OAuth2Auth(HttpBearer):
    def __init__(self, scopes: list[str] | None = None) -> None:
        super().__init__()
        self.scopes = scopes if scopes is not None else []

    def authenticate(self, request: HttpRequest, token: str) -> AccessToken | None:
        oauthlib_core = get_oauthlib_core()
        # This also sets `request.user`,
        # which Ninja does not: https://github.com/vitalik/django-ninja/issues/76
        valid, r = oauthlib_core.verify_request(request, scopes=self.scopes)

        if valid:
            # Any truthy return is success, but give the full AccessToken for Ninja to set as
            # `request.auth`.
            request.user = r.access_token.user
            return r.access_token
        return None


api = NinjaAPI(auth=OAuth2Auth())

api.add_router('/recording/', RecordingRouter)
api.add_router('/species/', SpeciesRouter)
api.add_router('/grts/', GRTSCellsRouter)
api.add_router('/guano/', GuanoMetadataRouter)
api.add_router('/recording-annotation/', RecordingAnnotationRouter)
api.add_router('/export-annotation/', ExportAnnotationRouter)
api.add_router('/configuration/', ConfigurationRouter)
api.add_router('/processing-task/', ProcessingTaskRouter)
api.add_router('/recording-tag/', RecordingTagRouter)
api.add_router('/nabat/recording/', NABatRecordingRouter)
api.add_router('/nabat/configuration/', NABatConfigurationRouter)
api.add_router('/vetting/', VettingRouter)
