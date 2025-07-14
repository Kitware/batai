import logging

from PIL import Image
from django.contrib.contenttypes.fields import GenericRelation
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel
import numpy as np

from bats_ai.core.models import SpectrogramImage

from .nabat_recording import NABatRecording

logger = logging.getLogger(__name__)


# TimeStampedModel also provides "created" and "modified" fields
class NABatSpectrogram(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    images = GenericRelation(SpectrogramImage)
    width = models.IntegerField()  # pixels
    height = models.IntegerField()  # pixels
    duration = models.IntegerField()  # milliseconds
    frequency_min = models.IntegerField()  # hz
    frequency_max = models.IntegerField()  # hz

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
        if not pil_images:
            return None  # Or raise an appropriate exception if this is unexpected

        np_images = [np.array(img) for img in pil_images]
        try:
            combined = np.hstack(np_images)
        except ValueError:
            combined = np.concatenate(np_images, axis=0)
        return combined

    class Meta:
        verbose_name = 'NABat Spectrogram'
        verbose_name_plural = 'NABat Spectrograms'
