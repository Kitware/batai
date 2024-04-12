import logging

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from .species import Species

logger = logging.getLogger(__name__)


COLORMAP = None
COLORMAP_ALLOWED = [None, 'gist_yarg', 'gnuplot2']


class colormap:
    def __init__(self, colormap=None):
        # Helpful aliases
        if colormap in ['none', 'default', 'dark']:
            colormap = None
        if colormap in ['light']:
            colormap = 'gist_yarg'
        if colormap in ['heatmap']:
            colormap = 'turbo'

        # Supported colormaps
        if colormap not in COLORMAP_ALLOWED:
            logging.warning(f'Substituted requested {colormap} colormap to default')
            logging.warning('See COLORMAP_ALLOWED')
            colormap = None

        self.colormap = colormap
        self.previous = None

    def __enter__(self):
        global COLORMAP

        self.previous = COLORMAP
        COLORMAP = self.colormap

    def __exit__(self, exc_type, exc_value, exc_tb):
        global COLORMAP

        COLORMAP = self.previous


# TimeStampedModel also provides "created" and "modified" fields
class Recording(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255)
    audio_file = models.FileField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    recorded_date = models.DateField(blank=True, null=True)
    recorded_time = models.TimeField(blank=True, null=True)
    equipment = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    recording_location = models.GeometryField(srid=4326, blank=True, null=True)
    grts_cell_id = models.IntegerField(blank=True, null=True)
    grts_cell = models.IntegerField(blank=True, null=True)
    public = models.BooleanField(default=False)
    software = models.TextField(blank=True, null=True)
    detector = models.TextField(blank=True, null=True)
    species_list = models.TextField(blank=True, null=True)
    site_name = models.TextField(blank=True, null=True)
    computed_species = models.ManyToManyField(
        Species, related_name='recording_computed_species'
    )  # species from a computed sense
    official_species = models.ManyToManyField(
        Species, related_name='recording_official_species'
    )  # species that are detemrined by the owner or from annotations as official species list
    unusual_occurrences = models.TextField(blank=True, null=True)

    @property
    def has_spectrogram(self):
        return len(self.spectrograms) > 0

    @property
    def spectrograms(self):
        from bats_ai.core.models import Spectrogram

        query = Spectrogram.objects.filter(recording=self, colormap=COLORMAP).order_by('-created')
        return query.all()

    @property
    def spectrogram(self):
        pass

        spectrograms = self.spectrograms

        assert len(spectrograms) >= 1
        spectrogram = spectrograms[0]  # most recently created

        return spectrogram


@receiver(models.signals.pre_delete, sender=Recording)
def delete_content(sender, instance, **kwargs):
    if instance.audio_file:
        instance.audio_file.delete(save=False)
