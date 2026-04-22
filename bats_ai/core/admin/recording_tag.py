from __future__ import annotations

from django.contrib import admin
from django.db.models import Count

from bats_ai.core.models import RecordingTag


@admin.register(RecordingTag)
class RecordingTagAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "text",
        "get_recording_count",
    ]
    search_fields = ["id", "user", "text"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(recording_count=Count("recording"))

    @admin.display(
        description="Number of recordings",
        ordering="recording_count",
    )
    def get_recording_count(self, obj):
        return obj.recording_count
