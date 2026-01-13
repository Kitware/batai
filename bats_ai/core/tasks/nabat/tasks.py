import logging
import os
from pathlib import Path
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.core.files import File
import requests

from bats_ai.core.models import Configuration, ProcessingTask, Species, SpectrogramImage
from bats_ai.core.models.nabat import (
    NABatCompressedSpectrogram,
    NABatRecording,
    NABatRecordingAnnotation,
    NABatSpectrogram,
)
from bats_ai.utils.spectrogram_utils import generate_spectrogram_assets, predict_from_compressed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')


def generate_spectrograms(
    self, nabat_recording: NABatRecording, presigned_url: str, processing_task: ProcessingTask
):
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = None
        try:
            file_response = requests.get(presigned_url, stream=True)
            if file_response.status_code == 200:
                audio_file = Path(f'{tmpdir}/audio_file.wav')
                with open(audio_file, 'wb') as temp_file:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)
        except Exception as e:
            logger.error(f'Error Downloading Presigned URL: {e}')
            processing_task.status = ProcessingTask.Status.ERROR
            processing_task.error = f'Error Downloading Presigned URL: {e}'
            processing_task.save()
            raise

        # Generate spectrogram assets
        logger.info('Generating spectrograms...')
        self.update_state(
            state='Progress',
            meta={'description': 'Generating Spectrograms'},
        )

        results = generate_spectrogram_assets(audio_file, tmpdir)

        self.update_state(
            state='Progress',
            meta={'description': 'Converting Spectrograms to Models'},
        )

        spectrogram, _ = NABatSpectrogram.objects.get_or_create(
            nabat_recording=nabat_recording,
            defaults={
                'width': results['normal']['width'],
                'height': results['normal']['height'],
                'duration': results['duration'],
                'frequency_min': results['freq_min'],
                'frequency_max': results['freq_max'],
            },
        )

        # Create SpectrogramImage objects for each normal image
        for idx, img_path in enumerate(results['normal']['paths']):
            with open(img_path, 'rb') as f:
                SpectrogramImage.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(spectrogram),
                    object_id=spectrogram.id,
                    index=idx,
                    defaults={
                        'image_file': File(f, name=os.path.basename(img_path)),
                        'type': 'spectrogram',
                    },
                )

        compressed = results['compressed']

        compressed_obj, _ = NABatCompressedSpectrogram.objects.get_or_create(
            nabat_recording=nabat_recording,
            spectrogram=spectrogram,
            defaults={
                'length': compressed['width'],
                'widths': compressed['widths'],
                'starts': compressed['starts'],
                'stops': compressed['stops'],
                'cache_invalidated': False,
            },
        )

        # Save compressed images
        for idx, img_path in enumerate(compressed['paths']):
            with open(img_path, 'rb') as f:
                SpectrogramImage.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(compressed_obj),
                    object_id=compressed_obj.id,
                    index=idx,
                    defaults={
                        'image_file': File(f, name=os.path.basename(img_path)),
                        'type': 'compressed',
                    },
                )

        try:
            config = Configuration.objects.first()
            if config and config.run_inference_on_upload:
                self.update_state(
                    state='Progress',
                    meta={'description': 'Running Prediction on Spectrogram'},
                )

                predict_results = predict_from_compressed(compressed_obj)
                label = predict_results['label']
                score = predict_results['score']
                confs = predict_results['confs']
                confidences = [
                    {'label': key, 'value': float(value)} for key, value in confs.items()
                ]
                sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
                output = {
                    'label': label,
                    'score': float(score),
                    'confidences': sorted_confidences,
                }
                species = Species.objects.filter(species_code=label)

                nabat_recording_annotation = NABatRecordingAnnotation.objects.create(
                    nabat_recording=compressed_obj.nabat_recording,
                    comments='Compressed Spectrogram Generation Prediction',
                    model='model.mobilenet.onnx',
                    confidence=output['score'],
                    additional_data=output,
                )
                nabat_recording_annotation.species.set(species)
                nabat_recording_annotation.save()

        except Exception as e:
            logger.error(f'Error Performing Prediction: {e}')
            processing_task.status = ProcessingTask.Status.ERROR
            processing_task.error = f'Error performing prediction: {e}'
            processing_task.save()
            raise

        processing_task.status = ProcessingTask.Status.COMPLETE
        processing_task.save()
