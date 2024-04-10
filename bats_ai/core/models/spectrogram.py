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
import tqdm

from bats_ai.core.models import Annotations, Recording

FREQ_MIN = 5e3
FREQ_MAX = 120e3
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
    colormap = models.CharField(max_length=20, blank=False, null=True)

    @classmethod
    def generate(cls, recording, colormap=None, dpi=600):
        """
        Ref: https://matplotlib.org/stable/users/explain/colors/colormaps.html
        """
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

        import IPython

        IPython.embed()

        # Function to take a signal and return a spectrogram.
        size = int(0.001 * sr)  # 1.0ms resolution
        size = 2 ** (math.ceil(math.log(size, 2)) + 0)
        hop_length = int(size / 4)

        # Short-time Fourier Transform
        window = librosa.stft(sig, n_fft=size, hop_length=hop_length, window='hamming')

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
        vmin = window.min()
        vmax = window.max()

        chunksize = int(2e3)
        arange = np.arange(chunksize, window.shape[1], chunksize)
        chunks = np.array_split(window, arange, axis=1)

        imgs = []
        for chunk in tqdm.tqdm(chunks):
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

            # Plot
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

        img = np.hstack(imgs)
        img = Image.fromarray(img, 'RGB')

        w, h = img.size
        # ratio = dpi / h
        # w_ = int(round(w * ratio))
        w_ = int(4.0 * duration * 1e3) * 2
        h_ = int(dpi) * 2
        img = img.resize((w_, h_), resample=Image.Resampling.LANCZOS)
        w, h = img.size

        img.save(f'/tmp/temp.{colormap}.jpg')

        img_filtered = cv2.imread(f'/tmp/temp.{colormap}.jpg', cv2.IMREAD_GRAYSCALE)
        img_filtered = img_filtered.astype(np.float32)
        assert img_filtered.min() == 0
        assert img_filtered.max() == 255
        img_filtered = img_filtered.astype(np.float32)
        img_filtered /= 0.9
        img_filtered[img_filtered < 0] = 0
        img_filtered[img_filtered > 255] = 255
        img_filtered = 255.0 - img_filtered

        kernel = np.ones((3, 3), np.uint8)
        # img_filtered = cv2.morphologyEx(img_filtered, cv2.MORPH_OPEN, kernel)
        img_filtered = cv2.erode(img_filtered, kernel, iterations=1)

        img_filtered = np.sqrt(img_filtered / 255.0) * 255.0

        img_filtered = np.around(img_filtered).astype(np.uint8)
        # img_filtered = cv2.resize(img_filtered, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        # img_filtered = cv2.medianBlur(img_filtered, 3)
        # img_filtered = cv2.resize(img_filtered, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_LINEAR)

        mask = img_filtered < 255 * 0.1
        img_filtered = cv2.applyColorMap(img_filtered, cv2.COLORMAP_TURBO)
        img_filtered[mask] = [0, 0, 0]

        cv2.imwrite('temp.png', img_filtered)

        # img_filtered = img.resize((w_, h_), resample=Image.Resampling.LANCZOS)
        # img_filtered = img_filtered.filter(ImageFilter.MedianFilter(size=3))
        # img_filtered = img_filtered.resize((w, h), resample=Image.Resampling.BILINEAR)
        # img_filtered.save(f'temp.{colormap}.median.jpg')

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
            colormap=colormap,
        )
        spectrogram.save()

    @property
    def compressed(self):
        img = self.image_np

        annotations = Annotations.objects.filter(recording=self.recording)

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
                start = annotation.start_time / self.duration
                stop = annotation.end_time / self.duration

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

                starts_.append(int(round(self.duration * (start / domain))))
                stops_.append(int(round(self.duration * (stop / domain))))
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

        canvas.save('temp.compressed.jpg')

        buf = io.BytesIO()
        canvas.save(buf, format='JPEG', quality=80)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        metadata = {
            'starts': starts_,
            'stops': stops_,
            'widths': widths,
            'length': total_width,
        }
        return canvas, img_base64, metadata

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

    def predict(self):
        import json
        import os

        import onnx
        import onnxruntime as ort
        import tqdm

        img, _, _ = self.compressed

        relative = ('..',) * 4
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
