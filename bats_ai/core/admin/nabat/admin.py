from django.contrib import admin

from bats_ai.core.models.nabat import (
    AcousticBatch,
    AcousticBatchAnnotation,
    NABatCompressedSpectrogram,
    NABatSpectrogram,
)


# Register models for the NaBat category
@admin.register(AcousticBatchAnnotation)
class AcousticBatchAnnotationAdmin(admin.ModelAdmin):
    list_display = (
        'acoustic_batch',
        'comments',
        'model',
        'confidence',
        'additional_data',
        'species_codes',
    )
    search_fields = ('acoustic_batch__name', 'comments', 'model')
    list_filter = ('acoustic_batch',)

    @admin.display(description='Species Codes')
    def species_codes(self, obj):
        # Assuming species have a `species_code` field
        return ', '.join([species.species_code for species in obj.species.all()])


@admin.register(NABatSpectrogram)
class NABatSpectrogramAdmin(admin.ModelAdmin):
    list_display = (
        'acoustic_batch',
        'image_file',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
        'colormap',
    )
    search_fields = ('acoustic_batch__name', 'colormap')
    list_filter = ('acoustic_batch', 'colormap')


@admin.register(NABatCompressedSpectrogram)
class NABatCompressedSpectrogramAdmin(admin.ModelAdmin):
    list_display = ('acoustic_batch', 'spectrogram', 'length', 'cache_invalidated')
    search_fields = ('acoustic_batch__name', 'spectrogram__id')
    list_filter = ('acoustic_batch', 'cache_invalidated')


@admin.register(AcousticBatch)
class AcousticBatchAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'batch_id',
        'equipment',
        'comments',
        'recording_location',
        'grts_cell_id',
        'grts_cell',
    )
    search_fields = ('name', 'batch_id', 'recording_location')
    list_filter = ('name', 'batch_id', 'recording_location')
