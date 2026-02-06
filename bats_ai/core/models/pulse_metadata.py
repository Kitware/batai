from django.contrib.gis.db import models

from .recording import Recording


class PulseMetadata(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    index = models.IntegerField(null=False, blank=False)
    bounding_box = models.PolygonField(null=False, blank=False)
    contours = models.JSONField(null=True, blank=True)
    # TODO: Add in metadata from batbot
