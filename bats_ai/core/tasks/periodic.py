from __future__ import annotations

from django.utils import timezone

from bats_ai.celery import app
from bats_ai.core.models import ExportedAnnotationFile


@app.task
def delete_expired_exported_files():
    now = timezone.now()
    expired_files = ExportedAnnotationFile.objects.filter(expires_at__lt=now)
    expired_files.delete()
