import io
import json
import logging
import math
import os
from typing import TypedDict

from PIL import Image
import cv2
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import onnx
import onnxruntime as ort
import scipy.signal
import tqdm

from bats_ai.core.models import CompressedSpectrogram
from bats_ai.core.models.nabat import NABatCompressedSpectrogram

logger = logging.getLogger(__name__)

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3


class SpectrogramAssetResult(TypedDict):
    paths: list[str]
    width: int
    height: int


class SpectrogramCompressedAssetResult(TypedDict):
    paths: list[str]
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

    # Load model path relative to this file
    relative = ('..',) * 4
    asset_path = os.path.abspath(os.path.join(__file__, *relative, 'assets'))
    onnx_filename = os.path.join(asset_path, 'model.mobilenet.onnx')
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

    return {'label': label, 'score': score, 'confgs': confs}


def generate_spectrogram_assets(
    recording_path: str, output_base: str, dpi: int = 520
) -> SpectrogramAssets:
    sig, sr = librosa.load(recording_path, sr=None)
    duration = len(sig) / sr

    size_mod = 1
    size = int(0.001 * sr)
    size = 2 ** (math.ceil(math.log(size, 2)) + size_mod)
    hop_length = int(size / 4)

    window = librosa.stft(sig, n_fft=size, hop_length=hop_length, window='hamming')
    window = np.abs(window) ** 2
    window = librosa.power_to_db(window)
    window -= np.median(window, axis=1, keepdims=True)
    window_ = window[window > 0]
    thresh = np.median(window_)
    window[window <= thresh] = 0

    bands = librosa.fft_frequencies(sr=sr, n_fft=size)
    for index in range(len(bands)):
        band_min = bands[index]
        band_max = bands[index + 1] if index < len(bands) - 1 else np.inf
        if band_max <= FREQ_MIN or FREQ_MAX <= band_min:
            window[index, :] = -1

    window = np.clip(window, 0, None)
    freq_low = int(FREQ_MIN - FREQ_PAD)
    freq_high = int(FREQ_MAX + FREQ_PAD)
    vmin = window.min()
    vmax = window.max()

    chunksize = int(2e3)
    arange = np.arange(chunksize, window.shape[1], chunksize)
    chunks = np.array_split(window, arange, axis=1)

    imgs = []
    for chunk in chunks:
        h, w = chunk.shape
        alpha = 3
        figsize = (int(math.ceil(w / h)) * alpha + 1, alpha)
        fig = plt.figure(figsize=figsize, facecolor='black', dpi=dpi)
        ax = plt.axes()
        plt.margins(0)

        kwargs = {
            'sr': sr,
            'n_fft': size,
            'hop_length': hop_length,
            'x_axis': 's',
            'y_axis': 'fft',
            'ax': ax,
            'vmin': vmin,
            'vmax': vmax,
        }

        librosa.display.specshow(chunk, cmap='gray', **kwargs)
        ax.set_ylim(freq_low, freq_high)
        ax.axis('off')

        buf = io.BytesIO()
        fig.savefig(buf, bbox_inches='tight', pad_inches=0)
        plt.close(fig)

        buf.seek(0)
        img = Image.open(buf)
        img = np.array(img)
        mask = img[:, :, -1]
        flags = np.where(np.sum(mask != 0, axis=0) == 0)[0]
        index = flags.min() if len(flags) > 0 else img.shape[1]
        img = img[:, :index, :3]

        imgs.append(img)

    normal_img = np.hstack(imgs)
    normal_width = int(8.0 * duration * 1e3)
    normal_height = 1200
    normal_img_resized = cv2.resize(
        normal_img, (normal_width, normal_height), interpolation=cv2.INTER_LANCZOS4
    )

    normal_out_path_base = os.path.join(
        os.path.dirname(output_base),
        'spectrogram',
        os.path.splitext(os.path.basename(output_base))[0] + '_spectrogram',
    )
    os.makedirs(os.path.dirname(normal_out_path_base), exist_ok=True)
    normal_paths = save_img(normal_img_resized, normal_out_path_base)

    compressed_img, compressed_paths, widths, starts, stops = generate_compressed(
        normal_img_resized, duration, output_base
    )

    result = {
        'duration': duration,
        'freq_min': freq_low,
        'freq_max': freq_high,
        'normal': {
            'paths': normal_paths,
            'width': normal_img_resized.shape[1],
            'height': normal_img_resized.shape[0],
        },
        'compressed': {
            'paths': compressed_paths,
            'width': compressed_img.shape[1],
            'height': compressed_img.shape[0],
            'widths': widths,
            'starts': starts,
            'stops': stops,
        },
    }

    return result


def generate_compressed(img: np.ndarray, duration: float, output_base: str):
    threshold = 0.5
    compressed_img = img.copy()
    starts, stops = [], []

    while True:
        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
        is_light = np.median(canvas) > 128.0
        if is_light:
            canvas = 255.0 - canvas

        amplitude = canvas.max(axis=0)
        amplitude -= amplitude.min()
        if amplitude.max() != 0:
            amplitude /= amplitude.max()
        amplitude[amplitude < threshold] = 0.0
        amplitude[amplitude > 0] = 1.0
        amplitude = amplitude.reshape(1, -1)

        canvas -= canvas.min()
        if canvas.max() != 0:
            canvas /= canvas.max()
        canvas *= 255.0
        canvas *= amplitude
        canvas = np.around(canvas).astype(np.uint8)

        mask = canvas.max(axis=0)
        mask = scipy.signal.medfilt(mask, 3)
        mask[0] = 0
        mask[-1] = 0

        starts, stops = [], []
        for index in range(1, len(mask) - 1):
            if mask[index] != 0:
                if mask[index - 1] == 0:
                    starts.append(index)
                if mask[index + 1] == 0:
                    stops.append(index)

        starts = [val - 40 for val in starts]
        stops = [val + 40 for val in stops]
        ranges = list(zip(starts, stops))

        while True:
            found = False
            merged = []
            index = 0
            while index < len(ranges) - 1:
                start1, stop1 = ranges[index]
                start2, stop2 = ranges[index + 1]

                # Clamp values within mask length
                start1 = min(max(start1, 0), len(mask))
                start2 = min(max(start2, 0), len(mask))
                stop1 = min(max(stop1, 0), len(mask))
                stop2 = min(max(stop2, 0), len(mask))

                if stop1 >= start2:
                    found = True
                    merged.append((start1, stop2))
                    index += 2
                else:
                    merged.append((start1, stop1))
                    index += 1
                if index == len(ranges) - 1:
                    merged.append((start2, stop2))
            ranges = merged
            if not found:
                break

        segments = []
        domain = img.shape[1]
        widths = []
        for start, stop in ranges:
            start_clamped = max(start, 0)
            stop_clamped = min(stop, domain)
            segment = img[:, start_clamped:stop_clamped]
            segments.append(segment)
            widths.append(stop_clamped - start_clamped)

        if segments:
            compressed_img = np.hstack(segments)
            break

        threshold -= 0.05
        if threshold < 0:
            compressed_img = img.copy()
            widths = []
            break

    # Convert starts and stops to time values relative to duration
    starts_time = [int(round(duration * (max(s, 0) / domain))) for s in starts]
    stops_time = [int(round(duration * (min(e, domain) / domain))) for e in stops]

    out_folder = os.path.join(os.path.dirname(output_base), 'compressed')
    os.makedirs(out_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(output_base))[0]
    compressed_out_path = os.path.join(out_folder, f'{base_name}_compressed')

    # save_img should be your existing function to save images and return file paths
    paths = save_img(compressed_img, compressed_out_path)

    return compressed_img, paths, widths, starts_time, stops_time


def save_img(img: np.ndarray, output_base: str):
    chunksize = int(5e4)
    length = img.shape[1]
    chunks = (
        np.split(img, np.arange(chunksize, length, chunksize), axis=1)
        if length > chunksize
        else [img]
    )
    total = len(chunks)
    output_paths = []
    for index, chunk in enumerate(chunks):
        out_path = f'{output_base}.{index + 1:02d}_of_{total:02d}.jpg'
        out_img = Image.fromarray(chunk, 'RGB')
        out_img.save(out_path, format='JPEG', optimize=True, quality=80)
        output_paths.append(out_path)
        logger.info(f'Saved image: {out_path}')

    return output_paths
