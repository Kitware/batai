from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from .recording import Recording
from .species import Species


class Annotations(TimeStampedModel, models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.FloatField(blank=True, null=True)
    end_time = models.FloatField(blank=True, null=True)
    low_freq = models.FloatField(blank=True, null=True)
    high_freq = models.FloatField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
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
