from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from bats_ai.core.models import Recording


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'audio_file', 'owner', 'recorded_date', 'equipment', 'comments', 'recording_location', 'grts_cell_id', 'grts_cell']
    list_select_related = True
    # list_select_related = ['owner']

    search_fields = ['name']

    autocomplete_fields = ['owner']
    readonly_fields = ['created', 'modified']

