from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel


class ExportedAnnotationFile(TimeStampedModel):
    file = models.FileField(upload_to='exports/')
    download_url = models.URLField(blank=True, null=True, max_length=2048)
    filters_applied = models.JSONField(
        blank=True,
        null=True,
    )
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=32,
        choices=[('pending', 'Pending'), ('complete', 'Complete'), ('failed', 'Failed')],
        default='pending',
    )

    class Meta:
        ordering = ['-created']


@receiver(models.signals.pre_delete, sender=ExportedAnnotationFile)
def delete_content(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
