from PIL import Image
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
import numpy as np

from .recording import Recording


class Spectrogram(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
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
    def image_url(self):
        return default_storage.url(self.image_file.name)


@receiver(models.signals.pre_delete, sender=Spectrogram)
def delete_content(sender, instance, **kwargs):
    if instance.image_file:
        instance.image_file.delete(save=False)
