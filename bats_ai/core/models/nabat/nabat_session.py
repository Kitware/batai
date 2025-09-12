from datetime import timedelta

from django.contrib.gis.db import models
from django.utils import timezone
from django_extensions.db.models import TimeStampedModel


class NABatSession(TimeStampedModel, models.Model):
    session_token = models.UUIDField()
    api_token = models.TextField(blank=False, null=False)
    refresh_token = models.TextField(blank=False, null=False)
    survey_event_id = models.TextField(blank=False, null=False)
    file_id = models.TextField(blank=False, null=False)
    user_id = models.TextField(blank=False, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at <= timezone.now()

    class Meta:
        verbose_name = 'NABat Session'
        verbose_name_plural = 'NABat Sessions'
