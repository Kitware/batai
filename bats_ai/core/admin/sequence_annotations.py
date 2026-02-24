from __future__ import annotations

from django.contrib import admin

from bats_ai.core.models import SequenceAnnotations


@admin.register(SequenceAnnotations)
class SequenceAnnotationsAdmin(admin.ModelAdmin):
    list_display = [
        "pk",
        "recording",
        "owner",
        "start_time",
        "end_time",
        "type",
        "comments",
    ]
    list_select_related = True
    autocomplete_fields = ["owner"]
