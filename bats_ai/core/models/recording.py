from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django_extensions.db.models import TimeStampedModel

FREQ_MIN = 5e3
FREQ_MAX = 200e3
FREQ_PAD = 2e3


# TimeStampedModel also provides "created" and "modified" fields
class Recording(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255)
    audio_file = models.FileField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    recorded_date = models.DateField(blank=True, null=True)
    equipment = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    recording_location = models.GeometryField(srid=0, blank=True, null=True)
    grts_cell_id = models.IntegerField(blank=True, null=True)
    grts_cell = models.IntegerField(blank=True, null=True)

    def generate_spectrogram(self):
        import base64
        import io
        from io import BytesIO
        import math

        from PIL import Image
        import django
        import librosa
        import matplotlib.pyplot as plt
        import numpy as np

        wav_file = self.audio_file
        try:
            if isinstance(wav_file, django.db.models.fields.files.FieldFile):
                sig, sr = librosa.load(BytesIO(wav_file.read()), sr=None)
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

        # Short-time Fourier Transform
        window = librosa.stft(sig, n_fft=size, window='hamming')

        # Calculating and processing data for the spectrogram.
        window = np.abs(window) ** 2
        window = librosa.power_to_db(window)

        # Denoise spectrogram
        window -= np.median(window, axis=1, keepdims=True)
        window -= np.median(window, axis=0, keepdims=True)

        bands = librosa.fft_frequencies(sr=sr, n_fft=size)
        for index in range(len(bands)):
            band_min = bands[index]
            band_max = bands[index + 1] if index < len(bands) - 1 else np.inf
            if band_max <= FREQ_MIN or FREQ_MAX <= band_min:
                window[index, :] = -1

        window = np.clip(window, 0, None)

        try:
            alpha = 8
            h, w = window.shape
            figsize = (int(math.ceil(w / h)) * alpha, alpha)
            fig = plt.figure(figsize=figsize, facecolor='black', dpi=100)
            ax = plt.axes()
            plt.margins(0)

            # Plot
            hop_length = int(size / 4)
            librosa.display.specshow(
                window, sr=sr, hop_length=hop_length, x_axis='s', y_axis='linear', ax=ax
            )

            freq_low = FREQ_MIN - FREQ_PAD
            freq_high = FREQ_MAX + FREQ_PAD
            ax.set_ylim(freq_low, freq_high)

            ax.axis('off')

            buf = io.BytesIO()
            fig.savefig(buf, bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            img = Image.open(buf)
            w, h = img.size

            import IPython
            IPython.embed()
            img.save('temp.png')

            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            img_base64 = base64.b64encode(buf.getvalue())
        finally:
            fig.clf()
            plt.close()

        # Return dictionary with all required fields
        return {
            'base64_spectrogram': img_base64,
            'spectroInfo': {
                'width': w,
                'height': h,
                'start_time': 0.0,
                'end_time': int(math.ceil(duration * 1000.0)),  # in milliseconds
                'low_freq': freq_low,
                'high_freq': freq_high,
            },
        }
