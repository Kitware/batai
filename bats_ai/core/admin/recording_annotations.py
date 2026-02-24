from __future__ import annotations

from django.contrib import admin

from bats_ai.core.models import RecordingAnnotation


@admin.register(RecordingAnnotation)
class RecordingAnnotationAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'recording',
        'owner',
        'species_codes',  # Add the custom field here
        'confidence',
        'additional_data',
        'comments',
        'model',
        'submitted',
    ]
    list_select_related = True
    filter_horizontal = ('species',)  # or filter_vertical
    autocomplete_fields = ['owner']

    # Custom method to display the species codes as a comma-separated string
    @admin.display(description='Species Codes')
    def species_codes(self, obj):
        # Assuming species have a `species_code` field
        return ', '.join([species.species_code for species in obj.species.all()])

    # Optionally, you can also add a verbose name for this field
