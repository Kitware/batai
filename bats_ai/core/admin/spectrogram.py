from django.contrib import admin

from bats_ai.core.models import Spectrogram
from django.db.models import QuerySet
from django.http import HttpRequest


@admin.register(Spectrogram)
class SpectrogramAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'recording',
        'colormap',
        'image_file',
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
        'image_file',
        'created',
        'modified',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
    ]

    actions = ['computed_compressed_spectrogram']


    @admin.action(description='Compute Compressed Spectrograms')
    def computed_compressed_spectrogram(self, request: HttpRequest, queryset: QuerySet):
        counter = 0
        for recording in queryset:
            if not recording.has_spectrogram:
                recording_compute_spectrogram.delay(recording.pk)
                counter += 1
        self.message_user(request, f'{counter} recordings queued', messages.SUCCESS)
