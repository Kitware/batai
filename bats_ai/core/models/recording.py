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
    recording_location = models.GeometryField(srid=4326, blank=True, null=True)
    grts_cell_id = models.IntegerField(blank=True, null=True)
    grts_cell = models.IntegerField(blank=True, null=True)
    public = models.BooleanField(default=False)

    @property
    def has_spectrogram(self):
        return len(self.spectrograms) > 0

    @property
    def spectrograms(self):
        from bats_ai.core.models import Spectrogram

        query = Spectrogram.objects.filter(recording=self).order_by('-created')
        return query.all()

    @property
    def spectrogram(self):
        from bats_ai.core.models import Spectrogram

        spectrograms = self.spectrograms

        if len(spectrograms) == 0:
            Spectrogram.generate(self)

            spectrograms = self.spectrograms
            assert len(spectrograms) == 1

        assert len(spectrograms) >= 1
        spectrogram = spectrograms[0]  # most recently created

        return spectrogram
