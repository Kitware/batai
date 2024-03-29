from celery import shared_task

from bats_ai.core.models import Image, Recording


@shared_task
def image_compute_checksum(image_id: int):
    image = Image.objects.get(pk=image_id)
    image.compute_checksum()
    image.save()


@shared_task
def recording_compute_spectrogram(recording_id: int):
    recording = Recording.objects.get(pk=recording_id)
    if not recording.has_spectrogram:
        recording.spectrogram  # compute by simply referenceing the attribute
        assert recording.has_spectrogram
