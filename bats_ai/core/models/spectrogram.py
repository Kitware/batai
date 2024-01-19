import base64
import io
import math

from PIL import Image
import cv2
from django.core.files import File
from django.db import models
from django.db.models.fields.files import FieldFile
from django_extensions.db.models import TimeStampedModel
import librosa
import matplotlib.pyplot as plt
import numpy as np
import scipy

from bats_ai.core.models import Recording

FREQ_MIN = 5e3
FREQ_MAX = 200e3
FREQ_PAD = 2e3


# TimeStampedModel also provides "created" and "modified" fields
class Spectrogram(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    image_file = models.FileField()
    width = models.IntegerField()  # pixels
    height = models.IntegerField()  # pixels
    duration = models.IntegerField()  # milliseconds
    frequency_min = models.IntegerField()  # hz
    frequency_max = models.IntegerField()  # hz

    @classmethod
    def generate(cls, recording):
        wav_file = recording.audio_file
        try:
            if isinstance(wav_file, FieldFile):
                sig, sr = librosa.load(io.BytesIO(wav_file.read()), sr=None)
                wav_file.name
            else:
                sig, sr = librosa.load(wav_file, sr=None)

            duration = len(sig) / sr
        except Exception as e:
            print(e)
            return None

        # Function to take a signal and return a spectrogram.
        size = int(0.001 * sr)  # 1.0ms resolution
        size = 2 ** math.ceil(math.log(size, 2))
        hop_length = int(size / 4)

        # Short-time Fourier Transform
        window = librosa.stft(sig, n_fft=size, window='hamming')

        # Calculating and processing data for the spectrogram.
        window = np.abs(window) ** 2
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
        dpi = 300

        chunksize = int(1e4)
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
                chunk, sr=sr, hop_length=hop_length, x_axis='s', y_axis='linear', ax=ax
            )

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

        img = np.hstack(imgs)
        img = Image.fromarray(img, 'RGB')

        w, h = img.size
        # ratio = dpi / h
        # w_ = int(round(w * ratio))
        w_ = int(4.0 * duration * 1e3)
        h_ = int(dpi)
        img = img.resize((w_, h_), resample=Image.Resampling.LANCZOS)
        w, h = img.size

        # img.save('temp.jpg')

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=80)
        buf.seek(0)

        name = 'spectrogram.jpg'
        image_file = File(buf, name=name)

        spectrogram = cls(
            recording_id=recording.pk,
            image_file=image_file,
            width=w,
            height=h,
            duration=math.ceil(duration * 1e3),
            frequency_min=freq_low,
            frequency_max=freq_high,
        )
        spectrogram.save()

    @property
    def compressed(self):
        img = self.image_np

        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        canvas = canvas.astype(np.float32)

        amplitude = canvas.max(axis=0)
        amplitude -= amplitude.min()
        amplitude /= amplitude.max()
        amplitude[amplitude < 0.5] = 0.0
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
        for start, stop in ranges:
            segment = img[:, start:stop]
            segments.append(segment)

            starts_.append(int(round(self.duration * (start / domain))))
            stops_.append(int(round(self.duration * (stop / domain))))

            # buffer = np.zeros((len(img), 20, 3), dtype=img.dtype)
            # segments.append(buffer)
        # segments = segments[:-1]

        canvas = np.hstack(segments)
        canvas = Image.fromarray(canvas, 'RGB')

        # canvas.save('temp.jpg')

        buf = io.BytesIO()
        canvas.save(buf, format='JPEG', quality=80)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        return img_base64, starts_, stops_

    @property
    def image_np(self):
        return np.array(self.image)

    @property
    def image_pil(self):
        return self.image

    @property
    def image(self):
        img = Image.open(self.image_file)
        return img

    @property
    def base64(self):
        img = self.image_file.read()
        img_base64 = base64.b64encode(img).decode('utf-8')

        return img_base64
