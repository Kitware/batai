from PIL import Image
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel
import numpy as np

from .recording import Recording
from .spectrogram import Spectrogram
from .spectrogram_image import SpectrogramImage


# TimeStampedModel also provides "created" and "modified" fields
class CompressedSpectrogram(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    spectrogram = models.ForeignKey(Spectrogram, on_delete=models.CASCADE)
    length = models.IntegerField()
    images = GenericRelation(SpectrogramImage)
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
        if not pil_images:
            if self.image_file:
                return np.array(Image.open(self.image_file))  # legacy
            return None

        np_images = [np.array(img) for img in pil_images]
        try:
            combined = np.hstack(np_images)
        except ValueError:
            # Fallback: stack along axis=0 if shapes don't match
            combined = np.concatenate(np_images, axis=0)
        return combined
