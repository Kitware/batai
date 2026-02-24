from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel

from .recording import Recording
from .spectrogram import Spectrogram
from .spectrogram_image import SpectrogramImage


# TimeStampedModel also provides "created" and "modified" fields
class CompressedSpectrogram(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    spectrogram = models.ForeignKey(Spectrogram, on_delete=models.CASCADE)
    length = models.FloatField()
    images = GenericRelation(SpectrogramImage)
    starts = ArrayField(ArrayField(models.FloatField()))
    stops = ArrayField(ArrayField(models.FloatField()))
    widths = ArrayField(ArrayField(models.FloatField()))
    cache_invalidated = models.BooleanField(default=True)

    @property
    def image_url_list(self):
        """Ordered list of image URLs for this spectrogram."""
        images = self.images.filter(type='compressed').order_by('index')
        return [default_storage.url(img.image_file.name) for img in images]

    @property
    def mask_url_list(self):
        """Ordered list of mask image URLs for this spectrogram."""
        images = self.images.filter(type='masks').order_by('index')
        return [default_storage.url(img.image_file.name) for img in images]
