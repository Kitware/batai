from PIL import Image
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel
import numpy as np

from bats_ai.core.models import SpectrogramImage

from .nabat_recording import NABatRecording
from .nabat_spectrogram import NABatSpectrogram


# TimeStampedModel also provides "created" and "modified" fields
class NABatCompressedSpectrogram(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    spectrogram = models.ForeignKey(NABatSpectrogram, on_delete=models.CASCADE)
    images = GenericRelation(SpectrogramImage)
    length = models.IntegerField()
    starts = ArrayField(ArrayField(models.IntegerField()))
    stops = ArrayField(ArrayField(models.IntegerField()))
    widths = ArrayField(ArrayField(models.IntegerField()))
    cache_invalidated = models.BooleanField(default=True)

    @property
    def image_url_list(self):
        """Ordered list of image URLs for this spectrogram."""
        images = self.images.filter(type='spectrogram').order_by('index')
        return [default_storage.url(img.image_file.name) for img in images]

    @property
    def image_pil_list(self):
        """List of PIL images in order."""
        images = self.images.filter(type='spectrogram').order_by('index')
        return [Image.open(img.image_file) for img in images]

    @property
    def image_np(self):
        """Combined image as a single numpy array by horizontal stacking."""
        pil_images = self.image_pil_list
        np_images = [np.array(img) for img in pil_images]
        try:
            combined = np.hstack(np_images)
        except ValueError:
            # Fallback: stack along axis=0 if shapes don't match
            combined = np.concatenate(np_images, axis=0)
        return combined

    class Meta:
        verbose_name = 'NABat Compressed Spectrogram'
        verbose_name_plural = 'NABat Compressed Spectrogram'
