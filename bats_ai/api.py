from ninja import NinjaAPI

from bats_ai.core.rest import RecordingRouter
api = NinjaAPI()

api.add_router('/recording/', RecordingRouter)
