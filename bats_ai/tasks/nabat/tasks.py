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

from bats_ai.core.models import Species
from bats_ai.core.models.nabat import (
    AcousticBatch,
    AcousticBatchAnnotation,
    NABatCompressedSpectrogram,
    NABatSpectrogram,
)

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3

COLORMAP_ALLOWED = [None, 'gist_yarg', 'turbo']


def generate_spectrogram(acoustic_batch, file, colormap=None, dpi=520):
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
            librosa.display.specshow(chunk, **kwargs)
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
    image_file = File(temp_file, name=f'{acoustic_batch.batch_id}_spectrogram.jpg')

    spectrogram = NABatSpectrogram.objects.create(
        acoustic_batch=acoustic_batch,
        image_file=image_file,
        width=w,
        height=h,
        duration=math.ceil(duration * 1e3),  # duration in ms
        frequency_min=freq_low,
        frequency_max=freq_high,
        colormap=colormap,
    )

    # Clean up temporary file
    temp_file.close()

    return spectrogram


def generate_compressed(spectrogram: NABatSpectrogram):
    img = spectrogram.image_np

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
def generate_compress_spectrogram(acoustic_batch_id: int, spectrogram_id: int):
    acoustic_batch = AcousticBatch.objects.get(pk=acoustic_batch_id)
    spectrogram = NABatSpectrogram.objects.get(pk=spectrogram_id)
    length, image_file, widths, starts, stops = generate_compressed(spectrogram)
    found = NABatCompressedSpectrogram.objects.filter(
        acoustic_batch=acoustic_batch_id, spectrogram=spectrogram
    )
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
        existing = NABatCompressedSpectrogram.objects.create(
            acoustic_batch=acoustic_batch,
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
    compressed_spectrogram = NABatCompressedSpectrogram.objects.get(pk=compressed_spectrogram_id)
    label, score, confs = compressed_spectrogram.predict()
    confidences = [{'label': key, 'value': float(value)} for key, value in confs.items()]
    sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
    output = {
        'label': label,
        'score': float(score),
        'confidences': sorted_confidences,
    }
    species = Species.objects.filter(species_code=label)

    acoustic_batch_annotation = AcousticBatchAnnotation.objects.create(
        acoustic_batch=compressed_spectrogram.acoustic_batch,
        comments='Compressed Spectrogram Generation Prediction',
        model='model.mobilenet.onnx',
        confidence=output['score'],
        additional_data=output,
    )
    acoustic_batch_annotation.species.set(species)
    acoustic_batch_annotation.save()
    return label, score, confs
