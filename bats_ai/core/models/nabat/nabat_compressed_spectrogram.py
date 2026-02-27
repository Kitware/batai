from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel

from bats_ai.core.models import SpectrogramImage

from .nabat_recording import NABatRecording
from .nabat_spectrogram import NABatSpectrogram


# TimeStampedModel also provides "created" and "modified" fields
class NABatCompressedSpectrogram(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    spectrogram = models.ForeignKey(NABatSpectrogram, on_delete=models.CASCADE)
    images = GenericRelation(SpectrogramImage)
    length = models.FloatField()
    starts = ArrayField(ArrayField(models.FloatField()))
    stops = ArrayField(ArrayField(models.FloatField()))
    widths = ArrayField(ArrayField(models.FloatField()))
    cache_invalidated = models.BooleanField(default=True)

    class Meta:
        verbose_name = "NABat Compressed Spectrogram"
        verbose_name_plural = "NABat Compressed Spectrogram"

    def __str__(self):
        return f"NABatCompressedSpectrogram {self.pk} (recording={self.nabat_recording_id})"

    @property
    def image_url_list(self):
        """Ordered list of image URLs for this spectrogram."""
        images = self.images.filter(type="compressed").order_by("index")
        return [default_storage.url(img.image_file.name) for img in images]

    @property
    def mask_url_list(self):
        """Ordered list of mask image URLs for this spectrogram."""
        images = self.images.filter(type="masks").order_by("index")
        return [default_storage.url(img.image_file.name) for img in images]
