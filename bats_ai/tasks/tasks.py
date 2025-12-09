import logging
import os
import tempfile

from PIL import Image
from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Polygon
from django.core.files import File

from bats_ai.core.models import (
    CompressedSpectrogram,
    ComputedPulseAnnotation,
    Configuration,
    Recording,
    RecordingAnnotation,
    Species,
    Spectrogram,
    SpectrogramImage,
    SpectrogramSvg,
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

        for idx, svg_path in enumerate(results['normal']['vectors']):
            with open(svg_path, 'rb') as f:
                SpectrogramSvg.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(spectrogram),
                    object_id=spectrogram.id,
                    index=idx,
                    defaults={
                        'type': 'spectrogram',
                        'image_file': File(f, name=os.path.basename(svg_path)),
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

        for idx, svg_path in enumerate(compressed['vectors']):
            with open(svg_path, 'rb') as f:
                SpectrogramSvg.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(compressed_obj),
                    object_id=compressed_obj.id,
                    index=idx,
                    defaults={
                        'image_file': File(f, name=os.path.basename(svg_path)),
                        'type': 'compressed',
                    },
                )

        # Generate computed annotations for contours
        logger.info(
            "Adding contour and bounding boxes for "
            f"{len(results.get('contours', []))} pulses"
        )
        for idx, contour in enumerate(results.get('contours', [])):
            # Transform contour (x, y) pairs into (time, freq) pairs
            widths, starts, stops = compressed['widths'], compressed['starts'], compressed['stops']
            start_time = starts[idx]
            end_time = stops[idx]
            width = widths[idx]
            time_per_pixel = (end_time - start_time) / width
            mhz_per_pixel = (results['freq_max'] - results['freq_min']) / compressed['height']
            transformed_lines = []
            for contour_line in contour:
                new_curve = [
                    [point[0] * time_per_pixel, point[1] * mhz_per_pixel]
                    for point in contour_line["curve"]
                ]
                transformed_lines.append({
                    "curve": new_curve,
                    "level": contour_line["level"],
                })
            ComputedPulseAnnotation.objects.get_or_create(
                index=idx,
                recording=recording,
                contours=transformed_lines,
                bounding_box=Polygon((
                    (start_time, results['freq_max']),
                    (end_time, results['freq_max']),
                    (end_time, results['freq_min']),
                    (start_time, results['freq_min']),
                    (start_time, results['freq_max']),
                )),
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
