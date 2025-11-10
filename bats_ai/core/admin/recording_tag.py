from django.contrib import admin

from bats_ai.core.models import RecordingTag


@admin.register(RecordingTag)
class RecordingTagAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'text',
    )
    search_fields = ('id', 'user', 'text')
