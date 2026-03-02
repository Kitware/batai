from __future__ import annotations

import logging

from ninja import NinjaAPI
from oauth2_provider.models import AccessToken

from bats_ai.core import views
from bats_ai.core.views import nabat

logger = logging.getLogger(__name__)


def global_auth(request):
    if request.user.is_anonymous:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if len(token) > 0:
            try:
                access_token = AccessToken.objects.get(token=token)
            except AccessToken.DoesNotExist:
                access_token = None
            if access_token and access_token.user and not access_token.user.is_anonymous:
                request.user = access_token.user
    user = request.user
    return (not user.is_anonymous) and (user.profile.verified or user.is_superuser)


api = NinjaAPI(auth=global_auth)

api.add_router("/recording/", views.recording_router)
api.add_router("/species/", views.species_router)
api.add_router("/grts/", views.grts_cells_router)
api.add_router("/guano/", views.guano_metadata_router)
api.add_router("/recording-annotation/", views.recording_annotation_router)
api.add_router("/export-annotation/", views.export_annotation_router)
api.add_router("/configuration/", views.configuration_router)
api.add_router("/processing-task/", views.processing_task_router)
api.add_router("/recording-tag/", views.recording_tag_router)
api.add_router("/vetting/", views.vetting_router)

api.add_router("/nabat/recording/", nabat.nabat_recording_router)
api.add_router("/nabat/configuration/", nabat.nabat_configuration_router)
