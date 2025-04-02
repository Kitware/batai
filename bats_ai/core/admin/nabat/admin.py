from django.contrib import admin

from bats_ai.core.models.nabat import (
    NABatCompressedSpectrogram,
    NABatRecording,
    NABatRecordingAnnotation,
    NABatSpectrogram,
)


# Register models for the NaBat category
@admin.register(NABatRecordingAnnotation)
class NABatRecordingAnnotationAdmin(admin.ModelAdmin):
    list_display = (
        'nabat_recording',
        'comments',
        'model',
        'confidence',
        'additional_data',
        'species_codes',
    )
    search_fields = ('nabat_recording_name', 'comments', 'model')
    list_filter = ('nabat_recording',)

    @admin.display(description='Species Codes')
    def species_codes(self, obj):
        # Assuming species have a `species_code` field
        return ', '.join([species.species_code for species in obj.species.all()])


@admin.register(NABatSpectrogram)
class NABatSpectrogramAdmin(admin.ModelAdmin):
    list_display = (
        'nabat_recording',
        'image_file',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
        'colormap',
    )
    search_fields = ('nabat_recording__name', 'colormap')
    list_filter = ('nabat_recording', 'colormap')


@admin.register(NABatCompressedSpectrogram)
class NABatCompressedSpectrogramAdmin(admin.ModelAdmin):
    list_display = ('nabat_recording', 'spectrogram', 'length', 'cache_invalidated')
    search_fields = ('nabat_recording__name', 'spectrogram__id')
    list_filter = ('nabat_recording', 'cache_invalidated')


@admin.register(NABatRecording)
class NABatRecordingAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'recording_id',
        'equipment',
        'comments',
        'recording_location',
        'grts_cell_id',
        'grts_cell',
    )
    search_fields = ('name', 'recording_id', 'recording_location')
    list_filter = ('name', 'recording_id', 'recording_location')
