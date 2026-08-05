from __future__ import annotations

from django.contrib.gis.db import models

from .nabat_recording import NABatRecording


class NABatPulseMetadata(models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    index = models.IntegerField(null=False, blank=False)
    bounding_box = models.PolygonField(null=False, blank=False)
    contours = models.JSONField(null=True, blank=True)
    curve = models.LineStringField(null=True, blank=True)
    char_freq = models.PointField(null=True, blank=True)
    knee = models.PointField(null=True, blank=True)
    heel = models.PointField(null=True, blank=True)
    slopes = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "NABat Pulse Metadata"
        verbose_name_plural = "NABat Pulse Metadata"
