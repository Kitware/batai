from __future__ import annotations

import logging

from django.contrib.contenttypes.fields import GenericRelation
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel

from bats_ai.core.models import SpectrogramImage

from .nabat_recording import NABatRecording

logger = logging.getLogger(__name__)


# TimeStampedModel also provides "created" and "modified" fields
class NABatSpectrogram(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    images = GenericRelation(SpectrogramImage)
    width = models.IntegerField()  # pixels
    height = models.IntegerField()  # pixels
    duration = models.FloatField()  # milliseconds
    frequency_min = models.FloatField()  # hz
    frequency_max = models.FloatField()  # hz

    class Meta:
        verbose_name = "NABat Spectrogram"
        verbose_name_plural = "NABat Spectrograms"

    def __str__(self):
        return f"NABatSpectrogram {self.pk} (recording={self.nabat_recording_id})"

    @property
    def image_url_list(self):
        """Ordered list of image URLs for this spectrogram."""
        images = self.images.filter(type="spectrogram").order_by("index")
        return [default_storage.url(img.image_file.name) for img in images]
