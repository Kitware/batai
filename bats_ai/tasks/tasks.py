import logging
import os
import tempfile

from PIL import Image
from celery import shared_task
from django.core.files import File

from bats_ai.core.models import (
    CompressedSpectrogram,
    Configuration,
    Recording,
    RecordingAnnotation,
    Species,
    Spectrogram,
)
from bats_ai.utils.spectrogram_utils import generate_spectrogram_assets, predict_from_compressed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')


@shared_task
def image_compute_checksum(image_id: int):
    image = Image.objects.get(pk=image_id)
    image.compute_checksum()
    image.save()


@shared_task
def recording_compute_spectrogram(recording_id: int):
    recording = Recording.objects.get(pk=recording_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        results = generate_spectrogram_assets(recording.audio_file, tmpdir)

        img_paths = results['normal']['paths']
        if len(img_paths) > 1:
            logger.error(
                'More than one image generated for recording, currently this not supported.'
            )
            raise ValueError(
                'More than one image generated for recording, currently this not supported.'
            )
        # Create or get Spectrogram
        image_path = img_paths[0] if img_paths else None
        if not image_path:
            logger.error('No image paths found in results, cannot create spectrogram.')
            raise ValueError('No image paths found in results, cannot create spectrogram.')
        with open(image_path, 'rb') as f:
            spectrogram, _ = Spectrogram.objects.get_or_create(
                recording=recording,
                defaults={
                    'width': results['normal']['width'],
                    'height': results['normal']['height'],
                    'duration': results['duration'],
                    'frequency_min': results['freq_min'],
                    'frequency_max': results['freq_max'],
                    'image_file': File(f, name=os.path.basename(image_path)),
                },
            )
        # Create or get CompressedSpectrogram
        compressed = results['compressed']
        compressed_img_paths = compressed['paths']
        if len(compressed_img_paths) > 1:
            logger.error(
                'More than one image generated for recording, currently this not supported.'
            )
            raise ValueError(
                'More than one image generated for recording, currently this not supported.'
            )
        # Create or get Spectrogram
        compressed_img_path = compressed_img_paths[0] if compressed_img_paths else None
        if not compressed_img_path:
            logger.error('No image paths found in results, cannot create spectrogram.')
            raise ValueError('No image paths found in results, cannot create spectrogram.')
        with open(compressed_img_path, 'rb') as f:
            compressed_obj, _ = CompressedSpectrogram.objects.get_or_create(
                recording=recording,
                spectrogram=spectrogram,
                defaults={
                    'length': compressed['width'],
                    'widths': compressed['widths'],
                    'starts': compressed['starts'],
                    'stops': compressed['stops'],
                    'cache_invalidated': False,
                    'image_file': File(f, name=os.path.basename(compressed_img_path)),
                },
            )

        config = Configuration.objects.first()
        if config and config.run_inference_on_upload:
            predict_results = predict_from_compressed(compressed_obj)
            label = predict_results['label']
            score = predict_results['score']
            confs = predict_results['confs']
            confidences = [{'label': key, 'value': float(value)} for key, value in confs.items()]
            sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
            output = {
                'label': label,
                'score': float(score),
                'confidences': sorted_confidences,
            }
            species = Species.objects.filter(species_code=label)

            recording_annotation = RecordingAnnotation.objects.create(
                recording=compressed_obj.recording,
                owner=compressed_obj.recording.owner,
                comments='Compressed Spectrogram Generation Prediction',
                model='model.mobilenet.onnx',
                confidence=output['score'],
                additional_data=output,
            )
            recording_annotation.species.set(species)
            recording_annotation.save()

        return {'spectrogram_id': spectrogram.id, 'compressed_id': compressed_obj.id}
