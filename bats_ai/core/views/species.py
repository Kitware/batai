from __future__ import annotations

import logging

from django.http import HttpRequest
from ninja import Schema
from ninja.pagination import RouterPaginated

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
    pk: int = None


@router.get("/", auth=None)
def get_species(request: HttpRequest):
    species = Species.objects.values()

    # Return the serialized data
    return list(species)
