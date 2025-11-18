from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.dispatch import receiver


def spectrogram_svg_upload_to(instance, filename):
    related = instance.content_object

    recording = getattr(related, 'recording', None) or getattr(related, 'nabat_recording', None)
    recording_id = getattr(recording, 'id', None)

    if not recording_id:
        raise ValueError('Related content must have a recording or nabat_recording.')

    return f'recording_{recording_id}/{instance.type}/svg_{instance.index}_{filename}'


class SpectrogramSvg(models.Model):
    SPECTROGRAM_TYPE_CHOICES = [
        ('spectrogram', 'Spectrogram'),
        ('compressed', 'Compressed'),
    ]
    content_object = GenericForeignKey('content_type', 'object_id')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    type = models.CharField(
        max_length=20,
        choices=SPECTROGRAM_TYPE_CHOICES,
        default='spectrogram',
    )
    index = models.PositiveIntegerField()
    image_file = models.FileField(upload_to=spectrogram_svg_upload_to)

    class Meta:
        ordering = ['index']


@receiver(models.signals.pre_delete, sender=SpectrogramSvg)
def delete_content(sender, instance, **kwargs):
    if instance.image_file:
        instance.image_file.delete(save=False)
