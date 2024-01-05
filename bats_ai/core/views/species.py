from datetime import datetime
import logging

from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.http import HttpRequest
from ninja import File, Form, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import RouterPaginated
from oauth2_provider.models import AccessToken

from bats_ai.core.models import Species

logger = logging.getLogger(__name__)


router = RouterPaginated()


class SpeciesSchema(Schema):
    species_code: str | None
    family: str | None
    genus: str | None
    species: str | None
    common_name: str | None
    species_code_6: str | None




@router.get('/')
def get_species(request: HttpRequest):
    species = Species.objects.values()

    # Return the serialized data
    return list(species)
