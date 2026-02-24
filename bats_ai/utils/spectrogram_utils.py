from __future__ import annotations

import logging
import os
from typing import TypedDict

from django.contrib.contenttypes.models import ContentType
from django.core.files import File

from bats_ai.core.models import SpectrogramImage
from bats_ai.core.models.nabat import NABatCompressedSpectrogram, NABatRecording, NABatSpectrogram

logger = logging.getLogger(__name__)


class SpectrogramAssetResult(TypedDict):
    paths: list[str]
    width: int
    height: int


class SpectrogramCompressedAssetResult(TypedDict):
    paths: list[str]
    masks: list[str]
    width: int
    height: int
    widths: list[float]
    starts: list[float]
    stops: list[float]


class SpectrogramAssets(TypedDict):
    duration: float
    freq_min: int
    freq_max: int
    normal: SpectrogramAssetResult
    compressed: SpectrogramCompressedAssetResult


class PredictionOutput(TypedDict):
    label: str
    score: float
    confs: dict[str, float]


def generate_nabat_spectrogram(
    nabat_recording: NABatRecording, results: SpectrogramAssets
) -> NABatSpectrogram:
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

    return spectrogram


def generate_nabat_compressed_spectrogram(
    nabat_recording: NABatRecording,
    spectrogram: NABatSpectrogram,
    compressed_results: SpectrogramCompressedAssetResult,
) -> NABatCompressedSpectrogram:
    compressed_obj, _ = NABatCompressedSpectrogram.objects.get_or_create(
        nabat_recording=nabat_recording,
        spectrogram=spectrogram,
        defaults={
            'length': compressed_results['width'],
            'widths': compressed_results['widths'],
            'starts': compressed_results['starts'],
            'stops': compressed_results['stops'],
            'cache_invalidated': False,
        },
    )

    # Save compressed images
    for idx, img_path in enumerate(compressed_results['paths']):
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
    for idx, mask_path in enumerate(compressed_results.get('masks', [])):
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

    return compressed_obj
