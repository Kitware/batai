import csv
from datetime import timedelta
from io import BytesIO
import zipfile

from celery import shared_task
from django.core.files import File
from django.utils.timezone import now

from bats_ai.core.models import ExportedAnnotationFile
from bats_ai.core.models.nabat import NABatRecordingAnnotation


def build_annotation_queryset(filters: dict):
    qs = NABatRecordingAnnotation.objects.all()

    if filters.get('start_date'):
        qs = qs.filter(created__date__gte=filters['start_date'])
    if filters.get('end_date'):
        qs = qs.filter(created__date__lte=filters['end_date'])
    if filters.get('recording_ids'):
        qs = qs.filter(nabat_recording__recording_id__in=filters['recording_ids'])
    if filters.get('usernames'):
        qs = qs.filter(user_email__in=filters['usernames'])
    if filters.get('min_confidence') is not None:
        qs = qs.filter(confidence__gte=filters['min_confidence'])
    if filters.get('max_confidence') is not None:
        qs = qs.filter(confidence__lte=filters['max_confidence'])

    return qs


@shared_task
def export_filtered_annotations_task(filters: dict, export_id: int):
    export_record = ExportedAnnotationFile.objects.get(pk=export_id)
    try:
        queryset = build_annotation_queryset(filters)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            csv_buffer = BytesIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(['id', 'user_email', 'confidence', 'comments', 'created', 'species'])

            for ann in queryset.prefetch_related('species'):
                species_names = ', '.join(s.common_name for s in ann.species.all())
                writer.writerow(
                    [
                        ann.id,
                        ann.user_email,
                        ann.confidence,
                        ann.comments,
                        ann.created.isoformat(),
                        species_names,
                    ]
                )
            zipf.writestr('annotations.csv', csv_buffer.getvalue().decode())

        buffer.seek(0)
        filename = f'export-{export_id}.zip'
        export_record.file.save(filename, File(buffer), save=False)
        export_record.download_url = export_record.file.url
        export_record.status = 'complete'
        export_record.expires_at = now() + timedelta(hours=24)
        export_record.save()
    except Exception as e:
        export_record.status = 'failed'
        export_record.save()
        raise e
