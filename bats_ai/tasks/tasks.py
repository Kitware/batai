import io
import math
import tempfile

from PIL import Image
from celery import shared_task
import cv2
from django.core.files import File
import librosa
import matplotlib.pyplot as plt
import numpy as np
import scipy

from bats_ai.core.models import (
    Annotations,
    CompressedSpectrogram,
    Configuration,
    Recording,
    RecordingAnnotation,
    Species,
    Spectrogram,
    colormap,
)

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3

COLORMAP_ALLOWED = [None, 'gist_yarg', 'turbo']


def generate_spectrogram(recording, file, colormap=None, dpi=520):
    try:
        sig, sr = librosa.load(file, sr=None)
        duration = len(sig) / sr
    except Exception as e:
        print(f'Error loading file: {e}')
        return None

    size_mod = 1
    high_res = False

    if colormap in ['inference']:
        colormap = None
        dpi = 300
        size_mod = 0
    if colormap in ['none', 'default', 'dark']:
        colormap = None
    if colormap in ['light']:
        colormap = 'gist_yarg'
    if colormap in ['heatmap']:
        colormap = 'turbo'
        high_res = True

    if colormap not in COLORMAP_ALLOWED:
        print(f'Substituted requested {colormap} colormap to default')
        colormap = None

    size = int(0.001 * sr)  # 1.0ms resolution
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

        if colormap is None:
            librosa.display.specshow(chunk, cmap='gray', **kwargs)
        else:
            librosa.display.specshow(chunk, cmap=colormap, **kwargs)

        ax.set_ylim(freq_low, freq_high)
        ax.axis('off')

        buf = io.BytesIO()
        fig.savefig(buf, bbox_inches='tight', pad_inches=0)

        fig.clf()
        plt.close()

        buf.seek(0)
        img = Image.open(buf)

        img = np.array(img)
        mask = img[:, :, -1]
        flags = np.where(np.sum(mask != 0, axis=0) == 0)[0]
        index = flags.min() if len(flags) > 0 else img.shape[1]
        img = img[:, :index, :3]

        imgs.append(img)

    w_ = int(8.0 * duration * 1e3)
    h_ = 1200

    img = np.hstack(imgs)
    img = cv2.resize(img, (w_, h_), interpolation=cv2.INTER_LANCZOS4)

    if high_res:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        noise = 0.1
        img = img.astype(np.float32)
        img -= img.min()
        img /= img.max()
        img *= 255.0
        img /= 1.0 - noise
        img[img < 0] = 0
        img[img > 255] = 255
        img = 255.0 - img

        img = cv2.blur(img, (9, 9))
        img = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
        img = cv2.blur(img, (9, 9))

        img -= img.min()
        img /= img.max()
        img *= 255.0

        mask = (img > 255 * noise).astype(np.float32)
        mask = cv2.blur(mask, (5, 5))

        img[img < 0] = 0
        img[img > 255] = 255
        img = np.around(img).astype(np.uint8)
        img = cv2.applyColorMap(img, cv2.COLORMAP_TURBO)

        img = img.astype(np.float32)
        img *= mask.reshape(*mask.shape, 1)
        img[img < 0] = 0
        img[img > 255] = 255
        img = np.around(img).astype(np.uint8)

    img = Image.fromarray(img, 'RGB')
    w, h = img.size

    # Save image to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    img.save(temp_file, format='JPEG', quality=80)
    temp_file.seek(0)

    # Create new NABatSpectrogram
    image_file = File(temp_file, name=f'{recording.id}_spectrogram.jpg')

    spectrogram = Spectrogram.objects.create(
        recording=recording,
        image_file=image_file,
        width=w,
        height=h,
        duration=math.ceil(duration * 1e3),  # duration in ms
        frequency_min=freq_low,
        frequency_max=freq_high,
        colormap=colormap,
    )

    spectrogram.save()
    # Clean up temporary file
    temp_file.close()

    return spectrogram


def generate_compressed(recording: Recording, spectrogram: Spectrogram):
    img = spectrogram.image_np
    annotations = Annotations.objects.filter(recording=recording)

    threshold = 0.5
    while True:
        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        canvas = canvas.astype(np.float32)

        is_light = np.median(canvas) > 128.0
        if is_light:
            canvas = 255.0 - canvas

        amplitude = canvas.max(axis=0)
        amplitude -= amplitude.min()
        amplitude /= amplitude.max()
        amplitude[amplitude < threshold] = 0.0
        amplitude[amplitude > 0] = 1.0
        amplitude = amplitude.reshape(1, -1)

        canvas -= canvas.min()
        canvas /= canvas.max()
        canvas *= 255.0
        canvas *= amplitude
        canvas = np.around(canvas).astype(np.uint8)

        width = canvas.shape[1]
        for annotation in annotations:
            start = annotation.start_time / spectrogram.duration
            stop = annotation.end_time / spectrogram.duration

            start = int(np.around(start * width))
            stop = int(np.around(stop * width))
            canvas[:, start : stop + 1] = 255.0

        mask = canvas.max(axis=0)
        mask = scipy.signal.medfilt(mask, 3)
        mask[0] = 0
        mask[-1] = 0

        starts = []
        stops = []
        for index in range(1, len(mask) - 1):
            value_pre = mask[index - 1]
            value = mask[index]
            value_post = mask[index + 1]
            if value != 0:
                if value_pre == 0:
                    starts.append(index)
                if value_post == 0:
                    stops.append(index)
        assert len(starts) == len(stops)

        starts = [val - 40 for val in starts]  # 10 ms buffer
        stops = [val + 40 for val in stops]  # 10 ms buffer
        ranges = list(zip(starts, stops))

        while True:
            found = False
            merged = []
            index = 0
            while index < len(ranges) - 1:
                start1, stop1 = ranges[index]
                start2, stop2 = ranges[index + 1]

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
                for index in range(1, len(ranges)):
                    start1, stop1 = ranges[index - 1]
                    start2, stop2 = ranges[index]
                    assert start1 < stop1
                    assert start2 < stop2
                    assert start1 < start2
                    assert stop1 < stop2
                    assert stop1 < start2
                break

        segments = []
        starts_ = []
        stops_ = []
        domain = img.shape[1]
        widths = []
        total_width = 0
        for start, stop in ranges:
            segment = img[:, start:stop]
            segments.append(segment)

            starts_.append(int(round(spectrogram.duration * (start / domain))))
            stops_.append(int(round(spectrogram.duration * (stop / domain))))
            widths.append(stop - start)
            total_width += stop - start

            # buffer = np.zeros((len(img), 20, 3), dtype=img.dtype)
            # segments.append(buffer)
        # segments = segments[:-1]

        if len(segments) > 0:
            break

        threshold -= 0.05
        if threshold < 0:
            segments = None
            break

    if segments is None:
        canvas = img.copy()
    else:
        canvas = np.hstack(segments)

    canvas = Image.fromarray(canvas, 'RGB')
    buf = io.BytesIO()
    canvas.save(buf, format='JPEG', quality=80)
    buf.seek(0)

    # Use temporary files
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        temp_file_name = temp_file.name
        canvas.save(temp_file_name)

        # Read the temporary file
        with open(temp_file_name, 'rb') as f:
            temp_file_content = f.read()

    # Wrap the content in BytesIO
    buf = io.BytesIO(temp_file_content)
    name = f'{spectrogram.pk}_spectrogram_compressed.jpg'
    image_file = File(buf, name=name)

    return total_width, image_file, widths, starts_, stops_


@shared_task
def image_compute_checksum(image_id: int):
    image = Image.objects.get(pk=image_id)
    image.compute_checksum()
    image.save()


@shared_task
def recording_compute_spectrogram(recording_id: int):
    recording = Recording.objects.get(pk=recording_id)

    cmaps = [
        None,  # Default (dark) spectrogram
        'light',  # Light spectrogram
    ]
    spectrogram_id = None
    for cmap in cmaps:
        with colormap(cmap):
            spectrogram_temp = generate_spectrogram(recording, recording.audio_file, cmap)
            if cmap is None:
                spectrogram_id = spectrogram_temp.pk
    if spectrogram_id is not None:
        compressed_spectro = generate_compress_spectrogram(recording_id, spectrogram_id)
        config = Configuration.objects.first()
        if config and config.run_inference_on_upload:
            predict(compressed_spectro.pk)


@shared_task
def generate_compress_spectrogram(recording_id: int, spectrogram_id: int):
    recording = Recording.objects.get(pk=recording_id)
    spectrogram = Spectrogram.objects.get(pk=spectrogram_id)
    length, image_file, widths, starts, stops = generate_compressed(recording, spectrogram)
    found = CompressedSpectrogram.objects.filter(recording=recording, spectrogram=spectrogram)
    if found.exists():
        existing = found.first()
        existing.length = length
        existing.image_file = image_file
        existing.widths = widths
        existing.starts = starts
        existing.stops = stops
        existing.cache_invalidated = False
        existing.save()
    else:
        existing = CompressedSpectrogram.objects.create(
            recording=recording,
            spectrogram=spectrogram,
            image_file=image_file,
            length=length,
            widths=widths,
            starts=starts,
            stops=stops,
            cache_invalidated=False,
        )
    return existing


@shared_task
def predict(compressed_spectrogram_id: int):
    compressed_spectrogram = CompressedSpectrogram.objects.get(pk=compressed_spectrogram_id)
    label, score, confs = predict_compressed(compressed_spectrogram.image_file)
    confidences = [{'label': key, 'value': float(value)} for key, value in confs.items()]
    sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
    output = {
        'label': label,
        'score': float(score),
        'confidences': sorted_confidences,
    }
    species = Species.objects.filter(species_code=label)

    recording_annotation = RecordingAnnotation.objects.create(
        recording=compressed_spectrogram.recording,
        owner=compressed_spectrogram.recording.owner,
        comments='Compressed Spectrogram Generation Prediction',
        model='model.mobilenet.onnx',
        confidence=output['score'],
        additional_data=output,
    )
    recording_annotation.species.set(species)
    recording_annotation.save()
    return label, score, confs


def predict_compressed(image_file):
    import json
    import os

    import onnx
    import onnxruntime as ort
    import tqdm

    img = Image.open(image_file)

    relative = ('..',) * 3
    asset_path = os.path.abspath(os.path.join(__file__, *relative, 'assets'))

    onnx_filename = os.path.join(asset_path, 'model.mobilenet.onnx')
    assert os.path.exists(onnx_filename)

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

    img = np.array(img)

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

    return label, score, confs
