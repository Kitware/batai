import io
import math
import os
from pathlib import Path
import random

from PIL import Image
import cv2
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
import numpy as np
import scipy
import tqdm

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3

WORKERS = 8

# brew install rubberband
# pip install tqdm scipy numpy matplotlib opencv-python-headless pillow ipython librosa soundfile samplerate resampy scikit-maad

def parallel(
    func,
    inputs,
    outputs,
    workers=WORKERS,
    assignment=False,
    threaded=False,
    quiet=True,
    desc=None,
):
    import concurrent.futures

    import tqdm

    if len(inputs) == 0:
        return None

    if threaded:
        executor_cls = concurrent.futures.ThreadPoolExecutor
    else:
        executor_cls = concurrent.futures.ProcessPoolExecutor

    workers = min(len(inputs), workers)

    with tqdm.tqdm(total=len(inputs), disable=quiet, desc=desc) as progress:
        with executor_cls(max_workers=workers) as executor:
            futures = [executor.submit(func, input_) for input_ in inputs]
            for future in concurrent.futures.as_completed(futures):
                key, data = future.result()
                if key is None:
                    outputs.update(data)
                elif assignment:
                    outputs[int(key)] = data
                else:
                    if key not in outputs:
                        outputs[key] = {}
                    outputs[key].update(data)
                progress.update(1)


def compute(wav_filepath, spectrogram_filepath):
    with open(wav_filepath, 'rb') as wav_file:
        sig, sr = librosa.load(wav_file, sr=None)

    duration = len(sig) / sr

    # Function to take a signal and return a spectrogram.
    size = int(0.001 * sr)  # 1.0ms resolution
    size = 2 ** math.ceil(math.log(size, 2))
    hop_length = int(size / 4)

    # Short-time Fourier Transform
    original = librosa.stft(sig, n_fft=size, window='hamming')

    # Calculating and processing data for the spectrogram.
    window = np.abs(original) ** 2
    window = librosa.power_to_db(window)

    # Denoise spectrogram
    # Subtract median frequency
    window -= np.median(window, axis=1, keepdims=True)

    # Subtract mean amplitude
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
    dpi = 300

    chunksize = int(1e3)
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

        # Plot
        librosa.display.specshow(
            chunk,
            sr=sr,
            hop_length=hop_length,
            x_axis='s',
            y_axis='linear',
            ax=ax,
            vmin=vmin,
            vmax=vmax,
        )

        ax.set_ylim(freq_low, freq_high)
        ax.axis('off')

        buf = io.BytesIO()
        fig.savefig(buf, bbox_inches='tight', pad_inches=0)

        fig.clf()
        plt.close()

        buf.seek(0)
        img = Image.open(buf)

        del buf

        img_ = np.array(img)
        img.close()
        img = img_

        mask = img[:, :, -1]
        flags = np.where(np.sum(mask != 0, axis=0) == 0)[0]
        index = flags.min() if len(flags) > 0 else img.shape[1]
        img = img[:, :index, :3]

        imgs.append(img)

    img = np.hstack(imgs)

    ratio = sum([chunk.shape[1] / chunks[0].shape[1] for chunk in chunks])
    val1 = imgs[0].shape[1] * ratio
    val2 = img.shape[1]
    scaling = val2 / val1

    img = Image.fromarray(img, 'RGB')

    w, h = img.size
    # ratio = dpi / h
    # w_ = int(round(w * ratio))
    w_ = int(4.0 * duration * 1e3)
    h_ = int(dpi)
    img = img.resize((w_, h_), resample=Image.Resampling.LANCZOS)
    w, h = img.size

    img_ = np.array(img)
    img.close()
    img = img_

    threshold = 0.5
    while True:
        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        canvas = canvas.astype(np.float32)

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
        percents = []
        width = img.shape[1]
        for start, stop in ranges:
            segment = img[:, start:stop]
            percents.append((
                start / width,
                stop / width
            ))
            segments.append(segment)
            # buffer = np.zeros((len(img), 20, 3), dtype=img.dtype)
            # segments.append(buffer)
        # segments = segments[:-1]

        if len(segments) > 0:
            break

        threshold -= 0.05
        if threshold < 0:
            segments = None
            percents = None
            break

    if segments is None:
        # raise ValueError()
        canvas = img.copy()
        percents = [(0.0, 1.0)]
    else:
        canvas = np.hstack(segments)

    width = original.shape[1] * scaling
    audios = []
    for start, stop in percents:
        start_ = (int(np.around(width * start)) // 2) * 2
        stop_ = (int(np.around(width * stop)) // 2) * 2
        audios.append(original[:, start_: stop_])
    audios = np.hstack(audios)

    waveform = librosa.istft(audios, n_fft=size, window='hamming')

    # wav_filepath_ = wav_filepath.replace('.wav', '.compressed.wav')
    # sf.write(wav_filepath_, waveform, samplerate=sr, format='wav')

    slowdown = 10
    sr_ = sr * slowdown
    sr_human = 44100
    ratio = int(sr / sr_human)

    waveform_ = librosa.resample(waveform, orig_sr=sr, target_sr=sr_, res_type='soxr_vhq')

    # wav_filepath_ = wav_filepath.replace('.wav', '.human.original.wav')
    # sf.write(wav_filepath_, waveform_, samplerate=sr, format='wav')

    waveform_ = scipy.signal.decimate(waveform_, ratio)

    wav_filepath_ = wav_filepath.replace('.wav', '.human.wav')
    sf.write(wav_filepath_, waveform_, samplerate=int(sr / ratio), format='wav')

    canvas = Image.fromarray(canvas, 'RGB')

    canvas.save(spectrogram_filepath)
    canvas.close()


def worker(inputs):
    position, wav_filepaths = inputs
    wav_filepaths = wav_filepaths.tolist()

    status = {}
    for wav_filepath in tqdm.tqdm(wav_filepaths, position=position):
        assert os.path.exists(wav_filepath)
        assert wav_filepath.endswith('.wav')
        spectrogram_filepath = wav_filepath.replace('.wav', '.jpg')
        wav_human_filepath = wav_filepath.replace('.wav', '.human.wav')

        flag = os.path.exists(spectrogram_filepath) and os.path.exists(wav_human_filepath)
        if flag:
            with Image.open(spectrogram_filepath) as image:
                w, h = image.size
                if h != 300 or w == 0:
                    flag = False

        if not flag:
            try:
                compute(wav_filepath, spectrogram_filepath)
            except Exception:
                raise

        flag = os.path.exists(spectrogram_filepath) and os.path.exists(wav_human_filepath)
        status[wav_filepath] = flag

    return None, status


if __name__ == '__main__':
    results = Path('/Users/jason.parham/Downloads/datasets').rglob('*.jpg')
    results = [str(path.absolute()) for path in results]
    results = set(results)

    paths = Path('/Users/jason.parham/Downloads/datasets').rglob('*.wav')
    paths = [str(path.absolute()) for path in paths]

    paths_ = []
    widths = []
    srs = []
    temps = {}
    for path in tqdm.tqdm(paths):
        if '.human.wav' in path:
            continue
        path_ = path.replace('.wav', '.jpg')
        path_human = path.replace('.wav', '.human.wav')

        if not os.path.exists(path_human):
            print(path)
            paths_.append(path)
        else:
            with open(path, 'rb') as wav_file:
                sig, sr = librosa.load(wav_file, sr=None)
            srs.append(sr)
            if sr not in temps:
                temps[sr] = []
            temps[sr].append(path)

        if path_ in results:
            image = Image.open(path_)
            w, h = image.size
            widths.append(w)
            if h != 300 or w < 50:
                print(path_, image.size)
                paths_.append(path)
        else:
            print(path)
            paths_.append(path)

    widths = np.array(widths)
    widths.sort()
    index = round(len(widths) * 0.005)
    print(np.sum(widths < 300) / len(widths))
    print(widths[:index])
    print(widths[-index:])
    print(widths.min())
    print(widths.max())
    print(widths.mean())
    print(widths.std())

    if len(srs) > 0:
        print(set(srs))
        for sr_ in sorted(set(srs)):
            print(sr_, srs.count(sr_))
            random.shuffle(temps[sr_])
            print(temps[sr_][:5])
        srs = np.array(srs)
        print(srs.min())
        print(srs.max())
        print(srs.mean())
        print(srs.std())

    random.shuffle(paths_)

    batches = np.array_split(paths_, 100)
    for batch in tqdm.tqdm(batches):
        if len(batch) == 0:
            continue
        chunks = np.array_split(batch, WORKERS)
        inputs = list(enumerate(chunks))
        founds = {}
        parallel(
            worker,
            inputs,
            founds,
        )
        founds = list(founds.values())
