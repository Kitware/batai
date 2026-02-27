from __future__ import annotations

from django.contrib import admin

from bats_ai.core.models import RecordingAnnotation
from bats_ai.core.models.recording_annotation import RecordingAnnotationSpecies


class RecordingAnnotationSpeciesInline(admin.TabularInline):
    model = RecordingAnnotationSpecies
    extra = 1
    autocomplete_fields = ["species"]
    ordering = ["order"]


@admin.register(RecordingAnnotation)
class RecordingAnnotationAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "recording",
        "owner",
        "species_codes",
        "confidence",
        "additional_data",
        "comments",
        "model",
        "submitted",
    ]
    list_select_related = True
    inlines = [RecordingAnnotationSpeciesInline]
    autocomplete_fields = ["owner"]

    @admin.display(description="Species Codes")
    def species_codes(self, obj):
        through = obj.recordingannotationspecies_set.order_by("order")
        return ", ".join(t.species.species_code for t in through)

    # Optionally, you can also add a verbose name for this field
