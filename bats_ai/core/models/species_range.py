from __future__ import annotations

from django.contrib.gis.db import models

from .species import Species


class SpeciesRange(models.Model):
    species = models.OneToOneField(
        Species,
        on_delete=models.CASCADE,
        related_name="range",
    )
    geom = models.GeometryField(srid=4326)
    source_feature_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional id from the source GeoJSON feature properties.",
    )
