from __future__ import annotations

import csv
from datetime import timedelta
from io import BytesIO, TextIOWrapper
import json
import logging
import zipfile

from django.core.files import File
from django.utils.timezone import now

from bats_ai.celery import app
from bats_ai.core.models import ExportedAnnotationFile
from bats_ai.core.models.nabat import NABatRecordingAnnotation

logger = logging.getLogger(__name__)


def build_annotation_queryset(filters: dict):
    qs = NABatRecordingAnnotation.objects.all()

    if filters.get("start_date"):
        qs = qs.filter(created__date__gte=filters["start_date"])
    if filters.get("end_date"):
        qs = qs.filter(created__date__lte=filters["end_date"])
    if filters.get("recording_ids"):
        qs = qs.filter(nabat_recording__recording_id__in=filters["recording_ids"])
    if filters.get("usernames"):
        qs = qs.filter(user_email__in=filters["usernames"])
    if filters.get("min_confidence") is not None:
        qs = qs.filter(confidence__gte=filters["min_confidence"])
    if filters.get("max_confidence") is not None:
        qs = qs.filter(confidence__lte=filters["max_confidence"])

    return qs


@app.task(bind=True)
def export_nabat_annotations_task(self, filters: dict, export_id: int):
    export_record = ExportedAnnotationFile.objects.get(pk=export_id)
    try:
        queryset = build_annotation_queryset(filters)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            # CSV creation
            csv_bytes = BytesIO()
            csv_buffer = TextIOWrapper(csv_bytes, encoding="utf-8", newline="")
            writer = csv.writer(csv_buffer)
            writer = csv.writer(csv_buffer)
            writer.writerow(
                [
                    "recording_id",
                    "recording_nameuser_email",
                    "confidence",
                    "created",
                    "species",
                    "comments",
                ]
            )

            annotations_data = []

            for ann in queryset.prefetch_related("species"):
                species_names = ", ".join(s.common_name for s in ann.species.all())
                logger.info("Exporting Ann: %s with species names: %s", ann, species_names)
                # Write row to CSV
                writer.writerow(
                    [
                        ann.nabat_recording.recording_id,
                        ann.nabat_recording.name,
                        ann.user_email,
                        ann.confidence,
                        ann.created.isoformat(),
                        species_names,
                        ann.comments,
                    ]
                )

                # Append to JSON structure
                annotations_data.append(
                    {
                        "recording_id": ann.nabat_recording.recording_id,
                        "recording_name": ann.nabat_recording.name,
                        "user_email": ann.user_email,
                        "confidence": ann.confidence,
                        "created": ann.created.isoformat(),
                        "species": [s.common_name for s in ann.species.all()],
                        "comments": ann.comments,
                    }
                )

            csv_buffer.flush()
            # Optional: reset cursor to the beginning (not strictly needed for getvalue())
            csv_bytes.seek(0)

            zipf.writestr("annotations.csv", csv_bytes.getvalue().decode())
            zipf.writestr("annotations.json", json.dumps(annotations_data, indent=2))

        buffer.seek(0)
        filename = f"export-{export_id}.zip"
        export_record.file.save(filename, File(buffer), save=False)
        logger.info("Export URL: %s", export_record.file.url)
        export_record.download_url = export_record.file.url
        export_record.status = "complete"
        export_record.expires_at = now() + timedelta(hours=24)
        export_record.save()
    except Exception:
        export_record.status = "failed"
        export_record.save()
        raise
