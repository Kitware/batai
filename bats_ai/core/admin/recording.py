from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.safestring import mark_safe

from bats_ai.core.models import Recording
from bats_ai.core.tasks import recording_compute_spectrogram


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'audio_file',
        'spectrogram_status',
        'owner',
        'recorded_date',
        'recorded_time',
        'public',
        'equipment',
        'comments',
        'recording_location',
        'grts_cell_id',
        'grts_cell',
    ]
    list_select_related = True
    # list_select_related = ['owner']

    search_fields = ['name']
    actions = ['compute_spectrograms']

    autocomplete_fields = ['owner']
    readonly_fields = ['created', 'modified']

    @admin.display(
        description='Spectrogram',
        empty_value='Not computed',
    )
    def spectrogram_status(self, recording: Recording):
        if recording.has_spectrogram:
            spectrogram = recording.spectrogram
            href = reverse('admin:core_spectrogram_change', args=(spectrogram.pk,))
            description = str(spectrogram)
            link = mark_safe(f'<a href="{href}">{description}</a>')
            return link
        return None

    @admin.action(description='Compute Spectrograms')
    def compute_spectrograms(self, request: HttpRequest, queryset: QuerySet):
        counter = 0
        for recording in queryset:
            if not recording.has_spectrogram:
                recording_compute_spectrogram.delay(recording.pk)
                counter += 1
        self.message_user(request, f'{counter} recordings queued', messages.SUCCESS)
