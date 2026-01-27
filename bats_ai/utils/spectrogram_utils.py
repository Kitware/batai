import json
import logging
import os
from pathlib import Path
from typing import TypedDict

import cv2
import numpy as np
import onnx
import onnxruntime as ort
import tqdm

from bats_ai.core.models import CompressedSpectrogram
from bats_ai.core.models.nabat import NABatCompressedSpectrogram

logger = logging.getLogger(__name__)


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
