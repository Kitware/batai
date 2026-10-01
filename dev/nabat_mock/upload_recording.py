#!/usr/bin/env python3
"""Uploads a .wav file into the nabat-mock minio bucket.

nabat-mock (see mock_server.py) always hands back a presigned URL for one fixed
object, regardless of which recording_id was requested. Run this once minio is up
to make that presigned URL resolve to real audio instead of 404ing:

    docker compose -f docker-compose.yml -f docker-compose-nabat-mock.yml up -d minio
    uv run dev/nabat_mock/upload_recording.py [path/to/some_recording.wav]

With no path given, uploads the repo's own assets/example.wav. The project's own
virtualenv already has the `minio` package (a transitive dependency via
django-minio-storage), so `uv run` needs no extra install.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import wave

from minio import Minio

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("upload-recording")

# Must match MINIO_BUCKET / RECORDING_OBJECT_KEY in mock_server.py - nabat-mock always
# hands back a presigned URL for this exact object, regardless of the requested recording.
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "nabat-mock")
RECORDING_OBJECT_KEY = "recordings/example.wav"

DEFAULT_WAV_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "example.wav"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=DEFAULT_WAV_PATH,
        help=f"Path to a .wav file to upload (default: {DEFAULT_WAV_PATH})",
    )
    return parser.parse_args()


def validate_wav(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{path} is not a file")
    if path.suffix.lower() != ".wav":
        raise SystemExit(f"{path} is not a .wav file")
    try:
        with wave.open(str(path), "rb"):
            pass
    except (wave.Error, EOFError) as e:
        raise SystemExit(f"{path} does not look like a valid WAV file: {e}") from e


def main() -> None:
    args = parse_args()
    validate_wav(args.path)

    client = Minio(
        os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.environ.get("MINIO_ACCESS_KEY", "minioAccessKey"),
        secret_key=os.environ.get("MINIO_SECRET_KEY", "minioSecretKey"),
        secure=False,
    )
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)

    client.fput_object(MINIO_BUCKET, RECORDING_OBJECT_KEY, str(args.path))
    logger.info("Uploaded %s to %s/%s", args.path, MINIO_BUCKET, RECORDING_OBJECT_KEY)


if __name__ == "__main__":
    main()
