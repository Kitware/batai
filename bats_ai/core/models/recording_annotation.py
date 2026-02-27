from __future__ import annotations

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from .recording import Recording
from .species import Species


class RecordingAnnotation(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    species = models.ManyToManyField(Species)
    comments = models.TextField(blank=True, null=True)
    # AI Model information if inference used, else "User Defined"
    model = models.TextField(blank=True, null=True)
    confidence = models.FloatField(
        default=1.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0),
        ],
        help_text="A confidence value between 0 and 1.0, default is 1.0.",
    )
    additional_data = models.JSONField(
        blank=True, null=True, help_text="Additional information about the models/data"
    )
    submitted = models.BooleanField(default=False)

    def __str__(self):
        return (
            f"RecordingAnnotation {self.pk} (recording={self.recording_id}, owner={self.owner_id})"
        )
