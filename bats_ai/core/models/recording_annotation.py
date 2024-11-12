from django.contrib.auth.models import User
from django.db import models

from .recording import Recording
from .species import Species


class RecordingAnnotation(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    species = models.ManyToManyField(Species)
    comments = models.TextField(blank=True, null=True)
