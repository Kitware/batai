from django.contrib.postgres.fields import ArrayField
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from .nabat_recording import NABatRecording
from .nabat_spectrogram import NABatSpectrogram


# TimeStampedModel also provides "created" and "modified" fields
class NABatCompressedSpectrogram(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    spectrogram = models.ForeignKey(NABatSpectrogram, on_delete=models.CASCADE)
    image_file = models.FileField()
    length = models.IntegerField()
    starts = ArrayField(ArrayField(models.IntegerField()))
    stops = ArrayField(ArrayField(models.IntegerField()))
    widths = ArrayField(ArrayField(models.IntegerField()))
    cache_invalidated = models.BooleanField(default=True)

    @property
    def image_url(self):
        return default_storage.url(self.image_file.name)

    class Meta:
        verbose_name = 'NABat Compressed Spectrogram'
        verbose_name_plural = 'NABat Compressed Spectrogram'


@receiver(models.signals.pre_delete, sender=NABatSpectrogram)
def delete_content(sender, instance, **kwargs):
    if instance.image_file:
        instance.image_file.delete(save=False)
