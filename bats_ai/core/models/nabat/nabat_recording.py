from __future__ import annotations

import logging

from django.contrib.gis.db import models
from django_extensions.db.models import TimeStampedModel

from bats_ai.core.models import Species

logger = logging.getLogger(__name__)


# TimeStampedModel also provides "created" and "modified" fields
class NABatRecording(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255)
    recording_id = models.BigIntegerField(blank=False, null=False, unique=True)
    survey_event_id = models.BigIntegerField(blank=False, null=False)
    acoustic_batch_id = models.BigIntegerField(blank=True, null=True)
    equipment = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    recording_location = models.GeometryField(srid=4326, blank=True, null=True)
    grts_cell_id = models.IntegerField(blank=True, null=True)
    grts_cell = models.IntegerField(blank=True, null=True)
    public = models.BooleanField(default=False)
    software_name = models.TextField(blank=True, null=True)
    software_developer = models.TextField(blank=True, null=True)
    software_version = models.TextField(blank=True, null=True)
    detector = models.TextField(blank=True, null=True)
    nabat_auto_species = models.ForeignKey(Species, null=True, on_delete=models.SET_NULL)
    nabat_manual_species = models.ForeignKey(Species, null=True, on_delete=models.SET_NULL)
    species_list = models.TextField(blank=True, null=True)
    nabat_auto_species = models.ForeignKey(
        Species, null=True, on_delete=models.SET_NULL, related_name="nabatrecording_auto_species"
    )
    nabat_manual_species = models.ForeignKey(
        Species, null=True, on_delete=models.SET_NULL, related_name="nabatrecording_manual_species"
    )
    computed_species = models.ManyToManyField(
        Species,
        related_name="nabatrecording_computed_species",  # Changed related name
    )  # species from a computed sense

    official_species = models.ManyToManyField(
        Species,
        related_name="nabatrecording_official_species",  # Changed related name
    )  # species that are detemrined by the owner or from annotations as official species list

    unusual_occurrences = models.TextField(blank=True, null=True)

    @property
    def has_spectrogram(self):
        return len(self.spectrograms) > 0

    @property
    def spectrograms(self):
        from bats_ai.core.models.nabat import NABatSpectrogram

        query = NABatSpectrogram.objects.filter(nabat_recording=self).order_by("-created")
        return query.all()

    @property
    def spectrogram(self):

        spectrograms = self.spectrograms

        assert len(spectrograms) >= 1
        spectrogram = spectrograms[0]  # most recently created

        return spectrogram

    @property
    def has_compressed_spectrogram(self):
        return len(self.compressed_spectrograms) > 0

    @property
    def compressed_spectrograms(self):
        from bats_ai.core.models.nabat import NABatCompressedSpectrogram

        query = NABatCompressedSpectrogram.objects.filter(nabat_recording=self).order_by("-created")
        return query.all()

    @property
    def compressed_spectrogram(self):

        compressed_spectrograms = self.compressed_spectrograms

        assert len(compressed_spectrograms) >= 1
        spectrogram = compressed_spectrograms[0]  # most recently created

        return spectrogram

    class Meta:
        verbose_name = "NABat Recording"
        verbose_name_plural = "NABat Recording"
