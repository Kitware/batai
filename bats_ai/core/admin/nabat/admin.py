from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib.gis.db import models as gis_models
from django.utils.html import format_html_join

from bats_ai.core.models.nabat import (
    NABatCompressedSpectrogram,
    NABatRecording,
    NABatRecordingAnnotation,
    NABatSpectrogram,
)
from bats_ai.core.models.nabat.nabat_pulse_metadata import NABatPulseMetadata


# Register models for the NaBat category
@admin.register(NABatRecordingAnnotation)
class NABatRecordingAnnotationAdmin(admin.ModelAdmin):
    list_display = [
        "nabat_recording",
        "comments",
        "model",
        "confidence",
        "additional_data",
        "species_codes",
    ]
    search_fields = ["nabat_recording_name", "comments", "model"]
    list_filter = ["nabat_recording"]

    @admin.display(description="Species Codes")
    def species_codes(self, obj):
        # Assuming species have a `species_code` field
        return ", ".join([species.species_code for species in obj.species.all()])


@admin.register(NABatSpectrogram)
class NABatSpectrogramAdmin(admin.ModelAdmin):
    list_display = [
        "nabat_recording",
        "width",
        "height",
        "duration",
        "frequency_min",
        "frequency_max",
        "image_url_list_display",
    ]
    search_fields = ["nabat_recording__name", "duration"]
    list_filter = ["nabat_recording", "duration"]

    @admin.display(description="Image URLs")
    def image_url_list_display(self, obj):
        """Render each image URL as a clickable link in admin detail view."""
        urls = obj.image_url_list
        if not urls:
            return "(No images)"
        return format_html_join(
            "\n", '<div><a href="{}" target="_blank">{}</a></div>', ((url, url) for url in urls)
        )


@admin.register(NABatCompressedSpectrogram)
class NABatCompressedSpectrogramAdmin(admin.ModelAdmin):
    list_display = [
        "nabat_recording",
        "spectrogram",
        "length",
        "cache_invalidated",
        "image_url_list_display",
    ]
    search_fields = ["nabat_recording__name", "spectrograms__id"]
    list_filter = ["nabat_recording", "cache_invalidated"]

    @admin.display(description="Image URLs")
    def image_url_list_display(self, obj):
        """Render each image URL as a clickable link in admin detail view."""
        urls = obj.image_url_list
        if not urls:
            return "(No images)"
        return format_html_join(
            "\n", '<div><a href="{}" target="_blank">{}</a></div>', ((url, url) for url in urls)
        )


@admin.register(NABatRecording)
class NABatRecordingAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "recording_id",
        "equipment",
        "comments",
        "recording_location",
        "grts_cell_id",
        "sample_frame_id",
    ]
    search_fields = ["name", "recording_id", "recording_location"]
    list_filter = ["name", "recording_id", "recording_location"]


@admin.register(NABatPulseMetadata)
class NABatPulseMetadataAdmin(admin.ModelAdmin):
    formfield_overrides = {
        gis_models.GeometryField: {
            "widget": forms.Textarea(attrs={"rows": 4, "cols": 80}),
        },
    }

    list_display = [
        "nabat_recording",
        "index",
        "bounding_box",
        "curve",
        "char_freq",
        "knee",
        "heel",
        "slopes",
    ]
    list_select_related = True
