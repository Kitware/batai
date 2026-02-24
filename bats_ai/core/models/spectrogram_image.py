from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.dispatch import receiver


def spectrogram_image_upload_to(instance, filename):
    related = instance.content_object

    recording = getattr(related, "recording", None) or getattr(related, "nabat_recording", None)
    recording_id = getattr(recording, "id", None)

    if not recording_id:
        raise ValueError("Related content must have a recording or nabat_recording.")

    return f"recording_{recording_id}/{instance.type}/image_{instance.index}_{filename}"


class SpectrogramImage(models.Model):
    SPECTROGRAM_TYPE_CHOICES = [
        ("spectrogram", "Spectrogram"),
        ("compressed", "Compressed"),
        ("masks", "Masks"),
    ]
    content_object = GenericForeignKey("content_type", "object_id")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    type = models.CharField(
        max_length=20,
        choices=SPECTROGRAM_TYPE_CHOICES,
        default="spectrogram",
    )
    index = models.PositiveIntegerField()
    image_file = models.FileField(upload_to=spectrogram_image_upload_to)  # temporary placeholder

    class Meta:
        ordering = ["index"]


@receiver(models.signals.pre_delete, sender=SpectrogramImage)
def delete_content(sender, instance, **kwargs):
    if not instance.image_file:
        return
    # Only delete the file if no other SpectrogramImage references the same path
    # (allows shared image references e.g. from copy_recordings management command)
    same_path_count = sender.objects.filter(image_file=instance.image_file.name).count()
    if same_path_count <= 1:
        instance.image_file.delete(save=False)
