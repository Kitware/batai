from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel

from .recording import Recording
from .spectrogram_image import SpectrogramImage


class Spectrogram(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    images = GenericRelation(SpectrogramImage)
    width = models.IntegerField()  # pixels
    height = models.IntegerField()  # pixels
    duration = models.FloatField()  # milliseconds
    frequency_min = models.FloatField()  # hz
    frequency_max = models.FloatField()  # hz

    @property
    def image_url_list(self):
        """Ordered list of image URLs for this spectrogram."""
        images = self.images.filter(type="spectrogram").order_by("index")
        return [default_storage.url(img.image_file.name) for img in images]
