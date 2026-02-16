from django.contrib import admin
from django.db.models import Count

from bats_ai.core.models import RecordingTag


@admin.register(RecordingTag)
class RecordingTagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'text',
        'recording_count',
    )
    search_fields = ('id', 'user', 'text')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_recording_count=Count('recording'))

    @admin.display(
        description='Number of recordings',
        ordering='_recording_count',
    )
    def recording_count(self, obj):
        return obj._recording_count
