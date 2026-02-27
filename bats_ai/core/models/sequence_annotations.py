from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models

from .recording import Recording
from .species import Species


class SequenceAnnotations(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.FloatField(blank=True, null=True)
    end_time = models.FloatField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    species = models.ManyToManyField(Species)

    def __str__(self):
        return (
            f"SequenceAnnotation {self.pk} (recording={self.recording_id}, owner={self.owner_id})"
        )
