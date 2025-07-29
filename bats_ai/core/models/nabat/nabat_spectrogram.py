import logging

from PIL import Image
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
import numpy as np

from .nabat_recording import NABatRecording

logger = logging.getLogger(__name__)


# TimeStampedModel also provides "created" and "modified" fields
class NABatSpectrogram(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    image_file = models.FileField()
    width = models.IntegerField()  # pixels
    height = models.IntegerField()  # pixels
    duration = models.IntegerField()  # milliseconds
    frequency_min = models.IntegerField()  # hz
    frequency_max = models.IntegerField()  # hz
    colormap = models.CharField(max_length=20, blank=False, null=True)

    @property
    def image_np(self):
        return np.array(self.image)

    @property
    def image_pil(self):
        img = Image.open(self.image_file)
        return img

    @property
    def image_url(self):
        return default_storage.url(self.image_file.name)

    class Meta:
        verbose_name = 'NABat Spectrogram'
        verbose_name_plural = 'NABat Spectrograms'


@receiver(models.signals.pre_delete, sender=NABatSpectrogram)
def delete_content(sender, instance, **kwargs):
    if instance.image_file:
        instance.image_file.delete(save=False)
