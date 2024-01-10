from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django_extensions.db.models import TimeStampedModel


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
        from io import BytesIO

        import librosa
        import librosa.display
        import matplotlib.pyplot as plt
        import numpy as np

        # Load audio file
        bytefile = self.audio_file.read()

        y, sr = librosa.load(BytesIO(bytefile))

        # Generate spectrogram
        D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)

        # Plot and save the spectrogram
        plt.figure(figsize=(10, 4))
        librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='linear')
        plt.colorbar(format='%+2.0f dB')
        plt.title('Spectrogram')
        plt.xlabel('Time')
        plt.ylabel('Frequency')
        plt.tight_layout()

        # Convert the plot to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        base64_image = base64.b64encode(buffer.read()).decode('utf-8')

        plt.close()

        start_time = 0.0
        end_time = librosa.get_duration(y=y, sr=sr) * 1000  # in milliseconds
        low_frequency = 0  # Set your desired low frequency
        high_frequency = sr / 2  # Set your desired high frequency
        image_width = 10 * 100  # 10 inches at 100 dpi
        image_height = 4 * 100  # 4 inches at 100 dpi

        # Return dictionary with all required fields
        return {
            'base64_spectrogram': base64_image,
            'spectroInfo': {
                'width': image_width,
                'height': image_height,
                'start_time': start_time,
                'end_time': end_time,
                'low_freq': low_frequency,
                'high_freq': high_frequency,
            },
        }
