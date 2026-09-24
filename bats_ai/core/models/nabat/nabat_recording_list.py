from __future__ import annotations

from django.contrib.gis.db import models
from django_extensions.db.models import TimeStampedModel

from .nabat_recording import NABatRecording


class NABatRecordingList(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    nabat_file_list_id = models.BigIntegerField(unique=True)
    nabat_project_id = models.BigIntegerField(blank=True, null=True)
    created_by_email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name = "NABat File List"
        verbose_name_plural = "NABat File Lists"

    def __str__(self):
        return self.name or f"{self.pk}: NABat File List {self.nabat_file_list_id}"


class NABatRecordingListItem(TimeStampedModel, models.Model):
    recording_list = models.ForeignKey(
        NABatRecordingList, on_delete=models.CASCADE, related_name="items"
    )
    nabat_recording = models.ForeignKey(
        NABatRecording, null=True, blank=True, on_delete=models.SET_NULL, related_name="list_items"
    )
    recording_time = models.DateTimeField(null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    recording_id = models.BigIntegerField()

    class Meta:
        verbose_name = "NABat File List Item"
        verbose_name_plural = "NABat File List Items"

        constraints = [
            models.UniqueConstraint(
                fields=["recording_list", "recording_id"],
                name="recording_once_per_list",
            ),
        ]

        ordering = ["-recording_time", "id"]
