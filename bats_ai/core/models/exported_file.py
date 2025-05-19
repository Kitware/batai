from django.db import models
from django_extensions.db.models import TimeStampedModel


class ExportedAnnotationFile(TimeStampedModel):
    file = models.FileField(upload_to='exports/')
    download_url = models.URLField(blank=True, null=True)
    filters_applied = models.JSONField(blank=True, null=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=32,
        choices=[('pending', 'Pending'), ('complete', 'Complete'), ('failed', 'Failed')],
        default='pending',
    )

    class Meta:
        ordering = ['-created']
