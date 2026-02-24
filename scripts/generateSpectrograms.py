from __future__ import annotations

import io
import json
import math
import os
import traceback

import click
import cv2
import librosa
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import tqdm

FREQ_MIN = 5e3
FREQ_MAX = 120e3
FREQ_PAD = 2e3

COLORMAP_ALLOWED = [None, 'gist_yarg', 'turbo']


def generate_spectrogram(wav_path, output_folder, colormap=None):
    try:
        sig, sr = librosa.load(wav_path, sr=None)
        duration = len(sig) / sr
        size_mod = 1
        high_res = False

        if colormap in ['inference']:
            colormap = None
            size_mod = 0
        elif colormap in ['none', 'default', 'dark']:
            colormap = None
        elif colormap in ['light']:
            colormap = 'gist_yarg'
        elif colormap in ['heatmap']:
            colormap = 'turbo'
            high_res = True

        if colormap not in COLORMAP_ALLOWED:
            click.echo(f'Substituted requested {colormap} colormap to default')
            colormap = None

        size = int(0.001 * sr)  # 1.0ms resolution
        size = 2 ** (math.ceil(math.log(size, 2)) + size_mod)
        hop_length = int(size / 4)

        window = librosa.stft(sig, n_fft=size, hop_length=hop_length, window='hamming')
        window = np.abs(window) ** 2
        window = librosa.power_to_db(window)

        # Denoise spectrogram
        window -= np.median(window, axis=1, keepdims=True)
        window_ = window[window > 0]
        thresh = np.median(window_)
        window[window <= thresh] = 0

        bands = librosa.fft_frequencies(sr=sr, n_fft=size)
        for index in range(len(bands)):
            band_min = bands[index]
            band_max = bands[index + 1] if index < len(bands) - 1 else np.inf
            if band_max <= FREQ_MIN or band_min >= FREQ_MAX:
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
        for chunk in tqdm.tqdm(chunks, desc=f'Processing {os.path.basename(wav_path)}'):
            h, w = chunk.shape
            alpha = 3
            figsize = (int(math.ceil(w / h)) * alpha + 1, alpha)
            fig = plt.figure(figsize=figsize, facecolor='black', dpi=300)
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
            plt.close(fig)

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
        output_path = os.path.join(
            output_folder, os.path.splitext(os.path.basename(wav_path))[0] + '.jpg'
        )
        img.save(output_path, format='JPEG', quality=80)

        return {'file': wav_path, 'status': 'success', 'output': output_path}

    except Exception as e:
        return {
            'file': wav_path,
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
        }


@click.command()
@click.argument('input_folder', type=click.Path(exists=True))
@click.argument('output_folder', type=click.Path(), default='./outputs')
@click.option(
    '--colormap',
    type=str,
    default=None,
    help='Colormap for spectrograms (default, light, heatmap).',
)
def process_wav_files(input_folder, output_folder, colormap):
    os.makedirs(output_folder, exist_ok=True)
    results = []

    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.wav'):
                wav_path = os.path.join(root, file)
                result = generate_spectrogram(wav_path, output_folder, colormap)
                results.append(result)

    results.sort(key=lambda x: x['status'], reverse=True)

    log_file = os.path.join(output_folder, 'conversion_log.json')
    with open(log_file, 'w') as f:
        json.dump(results, f, indent=4)

    click.echo(f'Processing complete. Log saved to {log_file}')


if __name__ == '__main__':
    process_wav_files()
