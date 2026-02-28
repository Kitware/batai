#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#     "click",
#     "Pillow",
#     "opencv-python-headless",
#     "faker",
#     "guano",
#     "librosa",
#     "matplotlib",
#     "numpy",
#     "pandas",
#     "scipy",
# ]
# ///
# "random" usage in this file is non-cryptographic
# ruff: noqa: S311
from __future__ import annotations

import io
import math
import os
from random import uniform

import click
import cv2
from faker import Faker
from guano import GuanoFile
import librosa
import librosa.display
import numpy as np
import pandas as pd
from PIL import Image
from scipy.io import wavfile
import scipy.signal

# === Constants ===

MIN_AUDIO_DURATION = 20
MAX_AUDIO_DURATION = 30
SAMPLE_RATE = 250_000

CHIRP_MIN_FREQ = 23_000
CHIRP_MAX_FREQ = 70_000
CHIRP_MIN_BANDWIDTH = 20_000
CHIRP_MAX_BANDWIDTH = 40_000
CHIRP_MIN_DURATION = 0.005
CHIRP_MAX_DURATION = 0.018
CHIRP_MIN_INTERVAL = 0.200
CHIRP_MAX_INTERVAL = 0.350

FREQ_MIN = 20000
FREQ_MAX = 90000
FREQ_PAD = 4000

COLORMAP_ALLOWED = [None, "gist_yarg", "turbo"]

LAT_MIN, LAT_MAX = 24.396308, 49.384358
LON_MIN, LON_MAX = -124.848974, -66.93457

faker = Faker()


def generate_random_us_latlon():
    lat = uniform(LAT_MIN, LAT_MAX)
    lon = uniform(LON_MIN, LON_MAX)
    return round(lat, 6), round(lon, 6)


def generate_chirp(start_freq, end_freq, duration, sample_rate):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return np.sin(2 * np.pi * np.linspace(start_freq, end_freq, len(t)) * t)


def generate_wav_file(filename, duration):
    total_samples = int(SAMPLE_RATE * duration)
    audio = np.zeros(total_samples, dtype=np.float32)

    t = 0.0
    while t < duration:
        interval = uniform(CHIRP_MIN_INTERVAL, CHIRP_MAX_INTERVAL)
        chirp_duration = uniform(CHIRP_MIN_DURATION, CHIRP_MAX_DURATION)
        if t + chirp_duration > duration:
            break

        start_freq = uniform(CHIRP_MIN_FREQ, CHIRP_MAX_FREQ - CHIRP_MIN_BANDWIDTH)
        end_freq = start_freq + uniform(CHIRP_MIN_BANDWIDTH, CHIRP_MAX_BANDWIDTH)
        chirp = generate_chirp(start_freq, end_freq, chirp_duration, SAMPLE_RATE)

        start_index = int(t * SAMPLE_RATE)
        end_index = start_index + len(chirp)
        if end_index <= total_samples:
            audio[start_index:end_index] += chirp
        t += interval

    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)
    wavfile.write(filename, SAMPLE_RATE, audio)

    gfile = GuanoFile(filename)
    lat, lon = generate_random_us_latlon()
    gfile["NABat|Latitude"] = str(lat)
    gfile["NABat|Longitude"] = str(lon)
    gfile["GUANO|Version"] = "1.0"
    gfile["Note"] = "Synthetic chirp for testing"
    gfile.write()


def generate_spectrogram(wav_path, output_path, colormap="turbo"):
    try:
        sig, sr = librosa.load(wav_path, sr=None)
        duration = len(sig) / sr
        size = 2 ** math.ceil(math.log2(0.001 * sr))
        hop_length = size // 4

        spec = librosa.stft(sig, n_fft=size, hop_length=hop_length, window="hamming")
        spec = librosa.power_to_db(np.abs(spec) ** 2)

        spec -= np.median(spec, axis=1, keepdims=True)
        thresh = np.median(spec[spec > 0])
        spec[spec <= thresh] = 0

        freqs = librosa.fft_frequencies(sr=sr, n_fft=size)
        for i, f in enumerate(freqs):
            if f < FREQ_MIN or f > FREQ_MAX:
                spec[i, :] = -1

        vmin, vmax = spec.min(), spec.max()

        fig, ax = plt.subplots(figsize=(12, 4))
        librosa.display.specshow(
            spec,
            sr=sr,
            hop_length=hop_length,
            x_axis="time",
            y_axis="linear",
            cmap=colormap,
            vmin=vmin,
            vmax=vmax,
            ax=ax,
        )
        ax.axis("off")

        buf = io.BytesIO()
        fig.savefig(buf, bbox_inches="tight", pad_inches=0)
        plt.close(fig)

        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        img.save(output_path, format="JPEG", quality=80)

        return output_path, duration

    except Exception as e:
        click.echo(f"Spectrogram error for {wav_path}: {e}")
        return None, None


def generate_compressed(img_path, duration, annotation_path, output_path):
    try:
        img = np.array(Image.open(img_path))
        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)

        is_light = np.median(canvas) > 128.0
        if is_light:
            canvas = 255.0 - canvas

        threshold = 0.5
        annotations = pd.read_csv(annotation_path)
        while True:
            amplitude = canvas.max(axis=0)
            amplitude -= amplitude.min()
            amplitude /= max(amplitude.max(), 1e-6)
            amplitude[amplitude < threshold] = 0
            amplitude[amplitude > 0] = 1
            amplitude = amplitude.reshape(1, -1)

            norm_canvas = (canvas - canvas.min()) / (canvas.max() - canvas.min())
            norm_canvas *= 255.0 * amplitude
            canvas_display = np.around(norm_canvas).astype(np.uint8)

            width = canvas_display.shape[1]
            for _, row in annotations.iterrows():
                start = round((row["start_time"] / duration) * width)
                stop = round((row["end_time"] / duration) * width)
                canvas_display[:, start : stop + 1] = 255

            mask = scipy.signal.medfilt(canvas_display.max(axis=0), 3)
            mask[0], mask[-1] = 0, 0

            starts, stops = [], []
            for i in range(1, len(mask) - 1):
                if mask[i] != 0:
                    if mask[i - 1] == 0:
                        starts.append(i - 40)
                    if mask[i + 1] == 0:
                        stops.append(i + 40)

            ranges = [
                (max(0, s), min(canvas.shape[1], e)) for s, e in zip(starts, stops, strict=False)
            ]
            if not ranges:
                threshold -= 0.05
                if threshold < 0:
                    break
                continue

            segments = [img[:, s:e] for s, e in ranges]
            if segments:
                final_img = np.hstack(segments)
                Image.fromarray(final_img).save(output_path, format="JPEG", quality=90)
                return True
            threshold -= 0.05

    except Exception as e:
        click.echo(f"Compression error: {e}")
    return False


@click.command()
@click.argument("num_files", type=int)
@click.option("--outdir", default="chirp_outputs", help="Output directory")
@click.option("--colormap", default=None, help="Colormap for spectrogram")
@click.option("--spectro", default=False, is_flag=True, help="Generate Spectrograms")
def main(num_files, outdir, colormap, spectro):
    """Generate synthetic chirp WAVs, spectrograms, and compressed outputs."""
    os.makedirs(outdir, exist_ok=True)

    for i in range(num_files):
        base = f"chirp_{i + 1:03}"
        wav_path = os.path.join(outdir, f"{base}.wav")
        spectrogram_path = os.path.join(outdir, f"{base}_spec.jpg")
        compressed_path = os.path.join(outdir, f"{base}_compressed.jpg")
        annotation_path = os.path.join(outdir, f"{base}.csv")

        duration = uniform(MIN_AUDIO_DURATION, MAX_AUDIO_DURATION)
        generate_wav_file(wav_path, duration)

        with open(annotation_path, "w") as f:
            f.write("start_time,end_time\n")
            f.write(f"{duration / 3:.2f},{2 * duration / 3:.2f}\n")  # dummy annotation
        if spectro:
            spec_img, spec_duration = generate_spectrogram(wav_path, spectrogram_path, colormap)
            if spec_img:
                success = generate_compressed(
                    spectrogram_path, spec_duration, annotation_path, compressed_path
                )
                click.echo(f"{base}: {'Success' if success else 'Failed'}")


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    main()
