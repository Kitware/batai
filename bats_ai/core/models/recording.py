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
        librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='log')
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

        return base64_image
