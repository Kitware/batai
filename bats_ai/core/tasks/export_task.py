from __future__ import annotations

import csv
from datetime import timedelta
from io import BytesIO
import json
import zipfile

from django.core.files import File
from django.utils.timezone import now

from bats_ai.celery import app
from bats_ai.core.models import (
    Annotations,
    ExportedAnnotationFile,
    RecordingAnnotation,
    SequenceAnnotations,
)


def build_filters(filters, has_confidence=False):
    conditions = {}
    if filters.get("start_date"):
        conditions["created__date__gte"] = filters["start_date"]
    if filters.get("end_date"):
        conditions["created__date__lte"] = filters["end_date"]
    if filters.get("recording_ids"):
        conditions["recording__id__in"] = filters["recording_ids"]
    if filters.get("usernames"):
        conditions["owner__username__in"] = filters["usernames"]
    if has_confidence:
        if filters.get("min_confidence") is not None:
            conditions["confidence__gte"] = filters["min_confidence"]
        if filters.get("max_confidence") is not None:
            conditions["confidence__lte"] = filters["max_confidence"]
    return conditions


def annotation_to_dict(
    annotation, include_times=False, include_freqs=False, include_confidence=False
):
    data = {
        "id": annotation.id,
        "recording_id": annotation.recording.id,
        "owner": annotation.owner.username,
        "comments": annotation.comments,
        "created": annotation.created.isoformat(),
        "species": [s.common_name for s in annotation.species.all()],
    }
    if include_times:
        data.update(
            {
                "start_time": annotation.start_time,
                "end_time": annotation.end_time,
            }
        )
    if include_freqs:
        data.update(
            {
                "low_freq": annotation.low_freq,
                "high_freq": annotation.high_freq,
            }
        )
    if include_confidence:
        data["confidence"] = annotation.confidence
    return data


def write_csv_and_json(
    zipf, name_prefix, queryset, include_times=False, include_freqs=False, include_confidence=False
):
    rows = [
        annotation_to_dict(
            ann,
            include_times=include_times,
            include_freqs=include_freqs,
            include_confidence=include_confidence,
        )
        for ann in queryset.prefetch_related("species")
    ]

    if not rows:
        return

    # Write CSV
    csv_buf = BytesIO()
    writer = csv.DictWriter(csv_buf, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    zipf.writestr(f"{name_prefix}_annotations.csv", csv_buf.getvalue().decode())

    # Write JSON
    zipf.writestr(f"{name_prefix}_annotations.json", json.dumps(rows, indent=2))


@app.task(bind=True)
def export_annotations_task(filters: dict, annotation_types: list, export_id: int):
    export_record = ExportedAnnotationFile.objects.get(pk=export_id)

    try:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            if "pulse" in annotation_types:
                pulse_filters = build_filters(filters, has_confidence=True)
                qs = Annotations.objects.filter(**pulse_filters)
                write_csv_and_json(
                    zipf,
                    "pulse",
                    qs,
                    include_times=True,
                    include_freqs=True,
                    include_confidence=True,
                )

            if "sequence" in annotation_types:
                sequence_filters = build_filters(filters, has_confidence=False)
                qs = SequenceAnnotations.objects.filter(**sequence_filters)
                write_csv_and_json(zipf, "sequence", qs, include_times=True)

            if "recording" in annotation_types:
                recording_filters = build_filters(filters, has_confidence=True)
                qs = RecordingAnnotation.objects.filter(**recording_filters)
                write_csv_and_json(zipf, "recording", qs, include_confidence=True)

        buffer.seek(0)
        filename = f"export-{export_id}.zip"
        export_record.file.save(filename, File(buffer), save=False)
        export_record.download_url = export_record.file.url
        export_record.status = "complete"
        export_record.expires_at = now() + timedelta(hours=24)
        export_record.save()

    except Exception:
        export_record.status = "failed"
        export_record.save()
        raise
