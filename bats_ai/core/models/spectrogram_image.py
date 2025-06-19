from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.dispatch import receiver


def spectrogram_image_upload_to(instance, filename):
    if not instance.recording_id or not instance.spectrogram_id:
        raise ValueError('recording and spectrogram must be saved before saving the image file.')

    return (
        f'recording_{instance.recording.id}/{instance.type}" f"/image_{instance.index}_{filename}'
    )


class SpectrogramImage(models.Model):
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
    image_file = models.FileField(upload_to=spectrogram_image_upload_to)  # temporary placeholder

    class Meta:
        ordering = ['index']


@receiver(models.signals.pre_delete, sender=SpectrogramImage)
def delete_content(sender, instance, **kwargs):
    if instance.image_file:
        instance.image_file.delete(save=False)
