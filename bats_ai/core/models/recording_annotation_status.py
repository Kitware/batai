from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel

from bats_ai.core.models import Recording


# TimeStampedModel also provides "created" and "modified" fields
class RecordingAnnotationStatus(TimeStampedModel, models.Model):
    class Status(models.TextChoices):
        COMPLETE = 'Complete'
        INPROGRESS = 'In Progress'
        ERROR = 'Error'

    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recording_status = models.CharField(
        max_length=255,  # If we need future states
        blank=True,
        help_text='Recording Annotation Status',
        choices=Status,
    )
