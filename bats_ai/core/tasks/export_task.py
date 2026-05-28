from __future__ import annotations

import csv
from datetime import timedelta
from io import BytesIO, StringIO
import json
from urllib.parse import urljoin
import zipfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.files.storage import default_storage
from django.db.models import Prefetch
from django.utils.timezone import now

from bats_ai.celery import app
from bats_ai.core.models import (
    Annotations,
    ExportedAnnotationFile,
    RecordingAnnotation,
    RecordingTag,
    SequenceAnnotations,
)
from bats_ai.core.models.recording_annotation import RecordingAnnotationSpecies


def build_filters(filters, *, has_confidence=False):
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


def _annotation_species_ordered(annotation):
    """Return species list in order; supports RecordingAnnotation and plain Many-to-Many."""
    if hasattr(annotation, "recordingannotationspecies_set"):
        # if it is an instance of RecordingAnnotation, use the through model
        species_ordered = annotation.recordingannotationspecies_set.order_by("order")
        return [t.species for t in species_ordered]
    return list(annotation.species.all())


def annotation_to_dict(
    annotation, *, include_times=False, include_freqs=False, include_confidence=False
):
    data = {
        "id": annotation.id,
        "recording_id": annotation.recording.id,
        "owner": annotation.owner.username,
        "comments": annotation.comments,
        "created": annotation.created.isoformat(),
        "species": [s.common_name for s in _annotation_species_ordered(annotation)],
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


def write_csv_and_json(  # noqa: PLR0913
    zipf,
    name_prefix,
    queryset,
    *,
    include_times=False,
    include_freqs=False,
    include_confidence=False,
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
                qs = RecordingAnnotation.objects.filter(**recording_filters).prefetch_related(
                    "recordingannotationspecies_set__species"
                )
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


@app.task(bind=True)
def export_tag_annotation_summary_task(self, export_id: int):
    export_record = ExportedAnnotationFile.objects.get(pk=export_id)
    try:
        tag_rows, tag_user_rows = _collect_tag_summary_rows()

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            _write_tag_exports(zipf, tag_rows, tag_user_rows)

        buffer.seek(0)
        filename = f"tag-annotation-summary-{export_id}.zip"
        export_record.file.save(filename, File(buffer), save=False)
        export_record.download_url = export_record.file.url
        export_record.status = "complete"
        export_record.expires_at = now() + timedelta(hours=24)
        export_record.save()
    except Exception:
        export_record.status = "failed"
        export_record.save()
        raise


@app.task(bind=True)
def export_recording_annotation_hierarchy_task(self, export_id: int):
    export_record = ExportedAnnotationFile.objects.get(pk=export_id)
    try:
        recordings_payload = _build_recording_annotations_payload()

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(
                "recording_annotations.json",
                json.dumps({"recordings": recordings_payload}, indent=2),
            )

        buffer.seek(0)
        filename = f"recording-annotations-{export_id}.zip"
        export_record.file.save(filename, File(buffer), save=False)
        export_record.download_url = export_record.file.url
        export_record.status = "complete"
        export_record.expires_at = now() + timedelta(hours=24)
        export_record.save()
    except Exception:
        export_record.status = "failed"
        export_record.save()
        raise


def _build_recording_annotations_payload():
    species_links_prefetch = Prefetch(
        "recordingannotationspecies_set",
        queryset=RecordingAnnotationSpecies.objects.select_related("species").order_by("order"),
        to_attr="ordered_species_links",
    )
    annotations = (
        RecordingAnnotation.objects.select_related("recording", "owner")
        .prefetch_related(species_links_prefetch)
        .order_by("recording_id", "id")
    )

    recordings_by_id = {}
    for annotation in annotations:
        recording = annotation.recording
        recording_entry = recordings_by_id.get(recording.id)
        if recording_entry is None:
            recording_entry = {
                "recording_id": recording.id,
                "filename": recording.name,
                "grts_cell_id": recording.grts_cell_id,
                "sample_frame_id": recording.sample_frame_id,
                "submitted_annotations": 0,
                "unsubmitted_annotations": 0,
                "spectrogram_url": urljoin(
                    settings.BATAI_WEB_URL, f"/recording/{recording.id}/spectrogram"
                ),
                "wav_download_url": (
                    default_storage.url(recording.audio_file.name) if recording.audio_file else None
                ),
                "annotations": [],
            }
            recordings_by_id[recording.id] = recording_entry

        if annotation.submitted:
            recording_entry["submitted_annotations"] += 1
        else:
            recording_entry["unsubmitted_annotations"] += 1

        species_codes = [
            species_link.species.species_code for species_link in annotation.ordered_species_links
        ]
        recording_entry["annotations"].append(
            {
                "annotation_id": annotation.id,
                "user": annotation.owner.username,
                "species_codes": species_codes,
                "confidence": annotation.confidence,
                "additional_data": annotation.additional_data,
                "comment": annotation.comments,
                "submitted": annotation.submitted,
            }
        )

    return list(recordings_by_id.values())


def _collect_tag_summary_rows():
    tag_rows = []
    tag_user_rows = []
    users = list(User.objects.order_by("username").values("id", "username"))
    tags = RecordingTag.objects.select_related("user").prefetch_related(
        "recording_set__recordingannotation_set__owner"
    )

    for tag in tags:
        tag_row, user_rows = _build_rows_for_tag(tag, users)
        tag_rows.append(tag_row)
        tag_user_rows.extend(user_rows)

    return tag_rows, tag_user_rows


def _build_rows_for_tag(tag, users):
    recordings = list(tag.recording_set.all())
    total_recordings = len(recordings)
    annotations_by_user = _group_recording_annotations_by_user(recordings)
    annotated_total, submitted_total, unsubmitted_total = _collect_total_sets(annotations_by_user)

    tag_row = {
        "tag_id": tag.id,
        "tag_text": tag.text,
        "tag_owner": tag.user.username,
        "total_recordings": total_recordings,
        "annotated_recordings": len(annotated_total),
        "submitted_recordings": len(submitted_total),
        "unsubmitted_recordings": len(unsubmitted_total),
        "remaining_recordings": total_recordings - len(annotated_total),
    }
    user_rows = _build_user_rows(
        tag,
        total_recordings,
        annotations_by_user,
        users,
    )
    return tag_row, user_rows


def _group_recording_annotations_by_user(recordings):
    annotations_by_user = {}
    for recording in recordings:
        for annotation in recording.recordingannotation_set.all():
            key = annotation.owner_id
            if key not in annotations_by_user:
                annotations_by_user[key] = {
                    "username": annotation.owner.username,
                    "annotated_recordings": set(),
                    "submitted_recordings": set(),
                    "unsubmitted_recordings": set(),
                }
            user_stats = annotations_by_user[key]
            user_stats["annotated_recordings"].add(recording.id)
            if annotation.submitted:
                user_stats["submitted_recordings"].add(recording.id)
            else:
                user_stats["unsubmitted_recordings"].add(recording.id)
    return annotations_by_user


def _collect_total_sets(annotations_by_user):
    annotated_total = set()
    submitted_total = set()
    unsubmitted_total = set()
    for user_stats in annotations_by_user.values():
        annotated_total.update(user_stats["annotated_recordings"])
        submitted_total.update(user_stats["submitted_recordings"])
        unsubmitted_total.update(user_stats["unsubmitted_recordings"])
    return annotated_total, submitted_total, unsubmitted_total


def _build_user_rows(tag, total_recordings, annotations_by_user, users):
    user_rows = []
    for user in users:
        owner_id = user["id"]
        username = user["username"]
        user_stats = annotations_by_user.get(owner_id)
        if user_stats is None:
            user_stats = {
                "username": username,
                "annotated_recordings": set(),
                "submitted_recordings": set(),
                "unsubmitted_recordings": set(),
            }
        annotated_count = len(user_stats["annotated_recordings"])
        user_rows.append(
            {
                "tag_id": tag.id,
                "tag_text": tag.text,
                "tag_owner": tag.user.username,
                "user_id": owner_id,
                "username": username,
                "total_recordings": total_recordings,
                "annotated_recordings": annotated_count,
                "submitted_recordings": len(user_stats["submitted_recordings"]),
                "unsubmitted_recordings": len(user_stats["unsubmitted_recordings"]),
                "remaining_recordings": total_recordings - annotated_count,
            }
        )
    return user_rows


def _write_tag_exports(zipf, tag_rows, tag_user_rows):
    tag_fieldnames = [
        "tag_id",
        "tag_text",
        "tag_owner",
        "total_recordings",
        "annotated_recordings",
        "submitted_recordings",
        "unsubmitted_recordings",
        "remaining_recordings",
    ]
    tag_user_fieldnames = [
        "tag_id",
        "tag_text",
        "tag_owner",
        "user_id",
        "username",
        "total_recordings",
        "annotated_recordings",
        "submitted_recordings",
        "unsubmitted_recordings",
        "remaining_recordings",
    ]

    tag_csv_buf = StringIO()
    tag_writer = csv.DictWriter(tag_csv_buf, fieldnames=tag_fieldnames)
    tag_writer.writeheader()
    for row in tag_rows:
        tag_writer.writerow(row)
    zipf.writestr("tag_summary.csv", tag_csv_buf.getvalue())

    tag_user_csv_buf = StringIO()
    tag_user_writer = csv.DictWriter(tag_user_csv_buf, fieldnames=tag_user_fieldnames)
    tag_user_writer.writeheader()
    for row in tag_user_rows:
        tag_user_writer.writerow(row)
    zipf.writestr("tag_summary_by_user.csv", tag_user_csv_buf.getvalue())

    users_payload = _build_users_payload(tag_user_rows)
    zipf.writestr(
        "tag_annotation_summary.json",
        json.dumps(
            {
                "users": users_payload,
            },
            indent=2,
        ),
    )


def _build_users_payload(tag_user_rows):
    users_by_id = {}
    for row in tag_user_rows:
        user_id = row["user_id"]
        if user_id not in users_by_id:
            users_by_id[user_id] = {
                "user_id": user_id,
                "username": row["username"],
                "tags": [],
            }

        tag_entry = {
            "tag_id": row["tag_id"],
            "tag_text": row["tag_text"],
            "tag_owner": row["tag_owner"],
            "has_annotations": row["annotated_recordings"] > 0,
        }
        if row["annotated_recordings"] > 0:
            tag_entry.update(
                {
                    "total_recordings": row["total_recordings"],
                    "annotated_recordings": row["annotated_recordings"],
                    "submitted_recordings": row["submitted_recordings"],
                    "unsubmitted_recordings": row["unsubmitted_recordings"],
                    "remaining_recordings": row["remaining_recordings"],
                }
            )
        else:
            tag_entry["annotated_recordings"] = 0
        users_by_id[user_id]["tags"].append(tag_entry)

    return sorted(users_by_id.values(), key=lambda user: user["username"])
