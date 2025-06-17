# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "librosa",
#     "matplotlib",
#     "numpy",
#     "opencv-python",
#     "pillow",
#     "scipy",
# ]
# ///


import io
import math
import os

from PIL import Image
import click
import cv2
import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal  # Ensure this is at the top with other imports

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3


def generate_spectrogram(file_path: str, output_base: str, dpi: int = 520) -> None:
    try:
        sig, sr = librosa.load(file_path, sr=None)
        duration = len(sig) / sr
    except Exception as e:
        raise click.ClickException(f'Error loading file: {e}')

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

    full_img = np.hstack(imgs)
    w_ = int(8.0 * duration * 1e3)
    h_ = 1200
    full_img = cv2.resize(full_img, (w_, h_), interpolation=cv2.INTER_LANCZOS4)

    out_folder = os.path.join(os.path.dirname(output_base), 'spectrogram')
    os.makedirs(out_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(output_base))[0]
    base_out_path = os.path.join(out_folder, f'{base_name}_spectrogram')

    save_img(full_img, base_out_path)

    generate_compressed(full_img, duration, output_base)


def generate_compressed(img: np.ndarray, duration: float, output_base: str) -> None:
    threshold = 0.5
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

        assert len(starts) == len(stops)
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

            starts_.append(int(round(duration * (start / domain))))
            stops_.append(int(round(duration * (stop / domain))))
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

    canvas = np.hstack(segments) if segments else img.copy()
    out_folder = os.path.join(os.path.dirname(output_base), 'compressed')
    os.makedirs(out_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(output_base))[0]
    base_out_path = os.path.join(out_folder, f'{base_name}_compressed')
    save_img(canvas, base_out_path)


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
        click.echo(f'Saved image: {out_path}')

    return output_paths


@click.command()
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False))
def main(input_file: str) -> None:
    """Generate a spectrogram JPEG from a WAV file."""
    if not input_file.lower().endswith(('.wav', '.mp3', '.flac', '.ogg', '.m4a')):
        raise click.ClickException('Input file must be an audio file (wav, mp3, flac, ogg, m4a)')

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    out_dir = os.path.join(os.path.dirname(input_file), base_name)
    output_path = os.path.join(out_dir, f'{base_name}.jpg')

    generate_spectrogram(input_file, output_path)


if __name__ == '__main__':
    main()
