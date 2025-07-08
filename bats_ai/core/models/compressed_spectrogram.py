from PIL import Image
from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
import numpy as np

from .recording import Recording
from .spectrogram import Spectrogram


# TimeStampedModel also provides "created" and "modified" fields
class CompressedSpectrogram(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    spectrogram = models.ForeignKey(Spectrogram, on_delete=models.CASCADE)
    image_file = models.FileField()
    length = models.IntegerField()
    starts = ArrayField(ArrayField(models.IntegerField()))
    stops = ArrayField(ArrayField(models.IntegerField()))
    widths = ArrayField(ArrayField(models.IntegerField()))
    cache_invalidated = models.BooleanField(default=True)

    @property
    def image_url(self):
        return default_storage.url(self.image_file.name)

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


@receiver(models.signals.pre_delete, sender=Spectrogram)
def delete_content(sender, instance, **kwargs):
    if instance.image_file:
        instance.image_file.delete(save=False)
