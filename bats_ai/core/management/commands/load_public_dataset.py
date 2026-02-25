from __future__ import annotations

import contextlib
from csv import DictReader
from datetime import date
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db.models import Q

from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Recording, RecordingTag
from bats_ai.core.tasks.tasks import recording_compute_spectrogram
from bats_ai.core.utils.guano_utils import extract_guano_metadata

logger = logging.getLogger(__name__)


def _get_owner(username: str | None) -> User | None:
    if username is None:
        return User.objects.filter(is_superuser=True).first()
    return User.objects.filter(username=username).first()


def _create_filename(s3_key: str) -> str:
    h = hashlib.sha256(s3_key.encode("utf-8")).hexdigest()
    suffix = Path(s3_key).suffix
    return f"{h}{suffix}"


def _get_metadata(filename: str, line: dict[str, str]) -> dict[str, Any]:
    metadata = {}
    guano_metadata = extract_guano_metadata(filename, check_filename=False)
    if guano_metadata.get("nabat_activation_start_time"):
        dt = guano_metadata["nabat_activation_start_time"]
        metadata["recorded_date"] = dt.date()
        metadata["recorded_time"] = dt.time()
    if guano_metadata.get("nabat_latitude") and guano_metadata.get("nabat_longitude"):
        metadata["point"] = Point(
            guano_metadata["nabat_longitude"], guano_metadata["nabat_latitude"]
        )
    if guano_metadata.get("nabat_grid_cell_grts_id"):
        with contextlib.suppress(ValueError, TypeError):
            metadata["grts_cell_id"] = int(guano_metadata["nabat_grid_cell_grts_id"])
    if guano_metadata.get("nabat_species_list"):
        metadata["species_list_str"] = ",".join(guano_metadata["nabat_species_list"])

    metadata["comments"] = guano_metadata.get("nabat_comments")
    metadata["detector_type"] = guano_metadata.get("nabat_detector_type")
    metadata["software_type"] = guano_metadata.get("nabat_software_type")
    metadata["site_name"] = guano_metadata.get("nabat_site_name")
    metadata["unusual_occurrences"] = guano_metadata.get("nabat_unusual_occurrences")

    if metadata.get("grts_cell_id") is None and line.get("grts_cell_id") is not None:
        metadata["grts_cell_id"] = line["grts_cell_id"]

    if metadata.get("recorded_date") is None and line.get("recording_night") is not None:
        # Expect this column to contain a string in YYYY-MM-DD format
        recording_night_parts = line["recording_night"].split("-")
        if len(recording_night_parts) == 3:
            year = int(recording_night_parts[0])
            month = int(recording_night_parts[1])
            day = int(recording_night_parts[2])
            metadata["recorded_date"] = date(year=year, month=month, day=day)

    return metadata


def _try_start_spectrogram_generation(recording_id: int):
    metadata_filter = {
        "type": ProcessingTaskType.SPECTROGRAM_GENERATION.value,
        "recording_id": recording_id,
    }

    processing_task = ProcessingTask.objects.filter(
        Q(metadata__contains=metadata_filter)
        & Q(status__in=[ProcessingTask.Status.RUNNING, ProcessingTask.Status.QUEUED])
    ).first()

    if processing_task:
        logger.info(f"  Spectrogram generation already started for recording {recording_id}")
    else:
        logger.info(f"  Generating spectrograms for existing recording {recording_id}")
        recording_compute_spectrogram.delay(recording_id)


def _ingest_files_from_manifest(
    s3_client,
    bucket: str,
    manifest: Path,
    owner: User,
    public: bool,
    limit: int | None,
    file_key: str = "file_key",
    tag_keys: list[str] | None = None,
):
    if tag_keys is None:
        tag_keys = []

    iterations = 0

    with open(manifest) as manifest_file:
        reader = DictReader(manifest_file)
        for line in reader:
            if limit and iterations >= limit:
                return
            iterations += 1
            existing_recording = None
            filename = None

            try:
                s3_key = line[file_key]
                existing_recording = Recording.objects.filter(name=s3_key).first()
                if existing_recording:
                    logger.info(f"A recording already exists for {s3_key}.")
                    _try_start_spectrogram_generation(existing_recording.pk)
                    continue
                logger.info(f"Ingesting {s3_key}...")
                filename = _create_filename(s3_key)
                logger.info(f"  Downloading to temporary file {filename}...")
                s3_client.download_file(bucket, s3_key, filename)
                logger.info(f"  Creating recording for {s3_key}")
                metadata = _get_metadata(filename, line)
                with open(filename, "rb") as f:
                    recording = Recording.objects.create(
                        name=s3_key,
                        owner=owner,
                        audio_file=File(f, name=filename),
                        recorded_date=metadata.get("recorded_date"),
                        recorded_time=metadata.get("recorded_time"),
                        equipment=None,
                        grts_cell_id=metadata.get("grts_cell_id"),
                        recording_location=metadata.get("point"),
                        public=public,
                        comments=metadata.get("comments"),
                        detector=metadata.get("detector_type"),
                        software=metadata.get("software_type"),
                        site_name=metadata.get("site_name"),
                        species_list=metadata.get("species_list_str", ""),
                        unusual_occurrences=metadata.get("unusual_occurrences"),
                    )
                    for tag_key in tag_keys:
                        tag_text = line.get(tag_key, None)
                        if not tag_text:
                            continue
                        tag, _created = RecordingTag.objects.get_or_create(
                            user=owner, text=tag_text
                        )
                        recording.tags.add(tag)
                # Trigger spectrogram task
                logger.info(
                    f"  Created recording with id {recording.pk} for {s3_key}."
                    " Starting task to generate spectrograms..."
                )
                recording_compute_spectrogram.delay(recording.pk)
            finally:
                if filename:
                    # Delete the file (this may run on a machine with limited resources)
                    try:
                        logger.info(f"  Cleaning up by removing temporary file {filename}...")
                        os.remove(filename)
                    except FileNotFoundError:
                        pass


class Command(BaseCommand):
    help = "Create recordings and spectrograms from WAV files in a public s3 bucket"

    def add_arguments(self, parser):
        parser.add_argument(
            "bucket", type=str, help="Name of a public S3 bucket where WAV files are stored"
        )
        parser.add_argument(
            "manifest",
            type=str,
            # Assume columns "Key" and "Tags"
            help="Manifest CSV file with file keys and tags",
        )
        parser.add_argument(
            "--owner",
            type=str,
            help="Username of the owner of the recordings. (Defaults to first superuser)",
        )
        parser.add_argument(
            "-p", "--public", action="store_true", help="Make imported recordings public"
        )
        parser.add_argument(
            "-l", "--limit", type=int, help="Limit the number of WAV files to be imported"
        )
        parser.add_argument(
            "--filekey",
            type=str,
            help="Column header denoting the AWS S3 file key.",
            default="file_key",
        )
        parser.add_argument(
            "--tags",
            type=str,
            help="Comma-delimited list of column headers to use as tags for uploaded recordings.",
        )

    def handle(self, *args, **options):
        bucket = options["bucket"]
        s3_client = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        try:
            s3_client.head_bucket(Bucket=bucket)
            self.stdout.write(self.style.SUCCESS(f"Found bucket {bucket}..."))
        except ClientError:
            self.stdout.write(self.style.ERROR(f"Could not access bucket {bucket}"))
            return
        manifest = Path(options["manifest"])
        if not manifest.exists():
            self.stdout.write(self.style.ERROR(f"Could not find manifest file {manifest}"))
        else:
            self.stdout.write(f"Using manifest file {manifest}...")

        owner = _get_owner(options.get("owner"))
        if not owner:
            self.stdout.write(
                self.style.ERROR("Could not find a user to assign ownership of the recordings")
            )
            return
        else:
            self.stdout.write(f"User {owner.username} will own the new files...")

        tag_keys_input = options.get("tags", "")
        if tag_keys_input:
            tag_keys = [tag.strip() for tag in tag_keys_input.split(",") if tag]

        public = options.get("public", False)
        limit = options.get("limit")
        file_key = options.get("filekey", "file_key")
        if limit:
            self.stdout.write(f"Ingesting the first {limit} files from {manifest}...")
        _ingest_files_from_manifest(
            s3_client,
            bucket,
            manifest,
            owner,
            public,
            limit,
            file_key=file_key,
            tag_keys=tag_keys,
        )
