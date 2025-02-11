import base64
import logging

from PIL import Image
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
import numpy as np

from .acoustic_batch import AcousticBatch

logger = logging.getLogger(__name__)

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3

COLORMAP_ALLOWED = [None, 'gist_yarg', 'turbo']


# TimeStampedModel also provides "created" and "modified" fields
class NABatSpectrogram(TimeStampedModel, models.Model):
    acoustic_batch = models.ForeignKey(AcousticBatch, on_delete=models.CASCADE)
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
        return self.image

    @property
    def image(self):
        img = Image.open(self.image_file)
        return img

    @property
    def base64(self):
        img = self.image_file.read()
        img_base64 = base64.b64encode(img).decode('utf-8')

        return img_base64

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
