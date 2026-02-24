from __future__ import annotations

import logging

from ninja import NinjaAPI
from oauth2_provider.models import AccessToken

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


def global_auth(request):
    if request.user.is_anonymous:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if len(token) > 0:
            try:
                access_token = AccessToken.objects.get(token=token)
            except AccessToken.DoesNotExist:
                access_token = None
            if access_token and access_token.user:
                if not access_token.user.is_anonymous:
                    request.user = access_token.user
    user = request.user
    return (not user.is_anonymous) and (user.profile.verified or user.is_superuser)


api = NinjaAPI(auth=global_auth)

api.add_router("/recording/", RecordingRouter)
api.add_router("/species/", SpeciesRouter)
api.add_router("/grts/", GRTSCellsRouter)
api.add_router("/guano/", GuanoMetadataRouter)
api.add_router("/recording-annotation/", RecordingAnnotationRouter)
api.add_router("/export-annotation/", ExportAnnotationRouter)
api.add_router("/configuration/", ConfigurationRouter)
api.add_router("/processing-task/", ProcessingTaskRouter)
api.add_router("/recording-tag/", RecordingTagRouter)
api.add_router("/nabat/recording/", NABatRecordingRouter)
api.add_router("/nabat/configuration/", NABatConfigurationRouter)
api.add_router("/vetting/", VettingRouter)
