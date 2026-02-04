import json
import logging
import os
from pathlib import Path
from typing import TypedDict

import cv2
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
import numpy as np
import onnx
import onnxruntime as ort
import tqdm

from bats_ai.core.models import CompressedSpectrogram, SpectrogramImage
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


def predict_from_compressed(
    compressed_object: CompressedSpectrogram | NABatCompressedSpectrogram,
) -> PredictionOutput:
    """
    Predict label, score, and confidences from an image file.

    Args:
        compressed_object: Compressed Spectrogram Object

    Returns:
        label (str): predicted label
        score (float): confidence score of the predicted label
        confs (dict): mapping label->confidence score for all labels
    """
    img = compressed_object.image_np
    if img is None:
        raise ValueError('No compressed spectrogram images found for prediction.')

    # TODO Eventually, this should be moved to a settings file or environment variable
    # Load model path relative to this file
    current_file = Path(__file__).resolve()

    # Go up 3 directories to reach the project root, then append 'assets/model.mobilenet.onnx'
    onnx_filename = current_file.parents[2] / 'assets' / 'model.mobilenet.onnx'
    assert os.path.exists(onnx_filename), f'ONNX model file not found at {onnx_filename}'

    session = ort.InferenceSession(
        onnx_filename,
        providers=[
            (
                'CUDAExecutionProvider',
                {
                    'cudnn_conv_use_max_workspace': '1',
                    'device_id': 0,
                    'cudnn_conv_algo_search': 'HEURISTIC',
                },
            ),
            'CPUExecutionProvider',
        ],
    )

    h, w, c = img.shape
    ratio_y = 224 / h
    ratio_x = ratio_y * 0.5
    raw = cv2.resize(img, None, fx=ratio_x, fy=ratio_y, interpolation=cv2.INTER_LANCZOS4)

    h, w, c = raw.shape
    if w <= h:
        canvas = np.zeros((h, h + 1, 3), dtype=raw.dtype)
        canvas[:, :w, :] = raw
        raw = canvas
        h, w, c = raw.shape

    inputs_ = []
    for index in range(0, w - h, 100):
        inputs_.append(raw[:, index : index + h, :])
    inputs_.append(raw[:, -h:, :])
    inputs_ = np.array(inputs_)

    chunksize = 1
    chunks = np.array_split(inputs_, np.arange(chunksize, len(inputs_), chunksize))
    outputs = []
    for chunk in tqdm.tqdm(chunks, desc='Inference'):
        outputs_ = session.run(
            None,
            {'input': chunk},
        )
        outputs.append(outputs_[0])
    outputs = np.vstack(outputs)
    outputs = outputs.mean(axis=0)

    model = onnx.load(onnx_filename)
    mapping = json.loads(model.metadata_props[0].value)
    labels = [mapping['forward'][str(index)] for index in range(len(mapping['forward']))]

    prediction = np.argmax(outputs)
    label = labels[prediction]
    score = outputs[prediction]
    confs = dict(zip(labels, outputs))

    return {'label': label, 'score': score, 'confs': confs}


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
