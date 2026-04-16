from __future__ import annotations

from django import forms
from django.contrib import admin
from django.contrib.gis.db import models as gis_models

from bats_ai.core.models import PulseMetadata


@admin.register(PulseMetadata)
class PulseMetadataAdmin(admin.ModelAdmin):
    # Geometries are spectrogram coordinates, not geographic: avoid OpenLayers
    # (projection/transform) and show WKT in a textarea instead.
    formfield_overrides = {
        gis_models.GeometryField: {
            "widget": forms.Textarea(attrs={"rows": 4, "cols": 80}),
        },
    }

    list_display = [
        "recording",
        "index",
        "bounding_box",
        "curve",
        "char_freq",
        "knee",
        "heel",
        "slopes",
    ]
    list_select_related = True
