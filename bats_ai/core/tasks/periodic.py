from celery import shared_task
from django.utils import timezone

from bats_ai.core.models import ExportedAnnotationFile


@shared_task
def delete_expired_exported_files():
    now = timezone.now()
    expired_files = ExportedAnnotationFile.objects.filter(expires_at__lt=now)
    expired_files.delete()
