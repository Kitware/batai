from __future__ import annotations

from django.contrib import admin

from bats_ai.core.models import PulseMetadata


@admin.register(PulseMetadata)
class PulseMetadataAdmin(admin.ModelAdmin):
    list_display = (
        "recording",
        "index",
        "bounding_box",
        "curve",
        "char_freq",
        "knee",
        "heel",
        "slopes",
    )
    list_select_related = True
