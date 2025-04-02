from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from bats_ai.core.models import Species

from .nabat_recording import NABatRecording


class NABatRecordingAnnotation(TimeStampedModel, models.Model):
    nabat_recording = models.ForeignKey(NABatRecording, on_delete=models.CASCADE)
    species = models.ManyToManyField(Species)
    comments = models.TextField(blank=True, null=True)
    model = models.TextField(blank=True, null=True)  # AI Model information if inference used
    confidence = models.FloatField(
        default=1.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(1.0),
        ],
        help_text='A confidence value between 0 and 1.0, default is 1.0.',
    )
    additional_data = models.JSONField(
        blank=True, null=True, help_text='Additional information about the models/data'
    )

    class Meta:
        verbose_name = 'NABat Recording Annotation'
        verbose_name_plural = 'NABat Recording Annotations'
