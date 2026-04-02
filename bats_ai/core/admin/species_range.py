from __future__ import annotations

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from bats_ai.core.models import SpeciesRange


@admin.register(SpeciesRange)
class SpeciesRangeAdmin(GISModelAdmin):
    list_display = (
        "id",
        "species",
        "source_feature_id",
    )
    list_select_related = ("species",)
    search_fields = (
        "species__species_code",
        "species__common_name",
        "source_feature_id",
    )
    autocomplete_fields = ("species",)
    ordering = ("species__species_code",)
