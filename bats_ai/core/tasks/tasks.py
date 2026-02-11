import logging
import os
import shutil
import tempfile

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Polygon
from django.core.files import File

from bats_ai.celery import app
from bats_ai.core.models import (
    CompressedSpectrogram,
    PulseMetadata,
    Recording,
    Spectrogram,
    SpectrogramImage,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')


@app.task
def recording_compute_spectrogram(recording_id: int):
    try:
        from bats_ai.core.utils.batbot_metadata import generate_spectrogram_assets
    except ImportError:
        raise RuntimeError(
            'Spectrogram generation requires additional dependencies specified by the '
            '[tasks] group.'
        )
    recording = Recording.objects.get(pk=recording_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy the audio file from FileField to a temporary file
        audio_filename = os.path.basename(recording.audio_file.name)
        temp_audio_path = os.path.join(tmpdir, audio_filename)

        with recording.audio_file.open('rb') as source_file:
            with open(temp_audio_path, 'wb') as dest_file:
                shutil.copyfileobj(source_file, dest_file)

        results = generate_spectrogram_assets(temp_audio_path, output_folder=tmpdir)
        # Create or get Spectrogram
        spectrogram, _ = Spectrogram.objects.get_or_create(
            recording=recording,
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

        # Create or get CompressedSpectrogram
        compressed = results['compressed']
        compressed_obj, _ = CompressedSpectrogram.objects.get_or_create(
            recording=recording,
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

        # Save mask images (from batbot metadata mask_path)
        for idx, mask_path in enumerate(compressed.get('masks', [])):
            with open(mask_path, 'rb') as f:
                SpectrogramImage.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(compressed_obj),
                    object_id=compressed_obj.id,
                    index=idx,
                    type='masks',
                    defaults={
                        'image_file': File(f, name=os.path.basename(mask_path)),
                    },
                )

        # Create SpectrogramContour objects for each segment
        for segment in results['segments']['segments']:
            PulseMetadata.objects.update_or_create(
                recording=compressed_obj.recording,
                index=segment['segment_index'],
                defaults={
                    'contours': segment.get('contours', []),
                    'bounding_box': Polygon(
                        (
                            (segment['start_ms'], segment['freq_max']),
                            (segment['stop_ms'], segment['freq_max']),
                            (segment['stop_ms'], segment['freq_min']),
                            (segment['start_ms'], segment['freq_min']),
                            (segment['start_ms'], segment['freq_max']),
                        )
                    ),
                },
            )

        return {'spectrogram_id': spectrogram.id, 'compressed_id': compressed_obj.id}
