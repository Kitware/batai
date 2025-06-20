from django.contrib import admin

from bats_ai.core.models import Spectrogram


@admin.register(Spectrogram)
class SpectrogramAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'recording',
        'colormap',
        'images',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
    ]
    list_display_links = ['pk', 'recording']
    list_select_related = True
    autocomplete_fields = ['recording']
    readonly_fields = [
        'recording',
        'colormap',
        'images',
        'created',
        'modified',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
    ]
