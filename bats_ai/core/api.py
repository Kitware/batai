from ninja import NinjaAPI
from resonant_utils.ninja import HttpOAuth2

from bats_ai.core import views
from bats_ai.core.views import nabat

api = NinjaAPI(auth=HttpOAuth2())

api.add_router('/recording/', views.RecordingRouter)
api.add_router('/species/', views.SpeciesRouter)
api.add_router('/grts/', views.GRTSCellsRouter)
api.add_router('/guano/', views.GuanoMetadataRouter)
api.add_router('/recording-annotation/', views.RecordingAnnotationRouter)
api.add_router('/export-annotation/', views.ExportAnnotationRouter)
api.add_router('/configuration/', views.ConfigurationRouter)
api.add_router('/processing-task/', views.ProcessingTaskRouter)
api.add_router('/recording-tag/', views.RecordingTagRouter)
api.add_router('/vetting/', views.VettingRouter)

api.add_router('/nabat/recording/', nabat.NABatRecordingRouter)
api.add_router('/nabat/configuration/', nabat.NABatConfigurationRouter)
