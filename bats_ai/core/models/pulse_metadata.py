from django.contrib.gis.db import models

from .recording import Recording


class PulseMetadata(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    index = models.IntegerField(null=False, blank=False)
    bounding_box = models.PolygonField(null=False, blank=False)
    contours = models.JSONField()
    curve = models.LineStringField(null=True, blank=True)
    char_freq = models.PointField(null=True, blank=True)
    knee = models.PointField(null=True, blank=True)
    heel = models.PointField(null=True, blank=True)
