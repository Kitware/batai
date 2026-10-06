#!/usr/bin/env python3
"""Minimal stand-in for NABat's GraphQL API, for local dev/testing.

BatAI never uses a real GraphQL client: every query is a plain string,
interpolated with literal IDs and POSTed as {"query": "..."}, with no
variables and no schema. So instead of running a GraphQL server, this
dispatches on substrings in the query text and returns canned JSON shaped
like NABat's real responses.

Scope (for now): the single-recording fetch flow and the file-list create flow, i.e.
the query shapes used by:
  - bats_ai/core/tasks/nabat/nabat_data_retrieval.py (fetchAcousticAndSurveyEventInfo)
  - bats_ai/core/views/nabat/nabat_recording.py (bare presignedUrlFromAcousticFile,
    used as an access check by get_email_if_authorized / generate_nabat_recording;
    and the updateAcousticFileVet mutation, used to push an annotation to NABat)
  - bats_ai/core/views/nabat/nabat_file_list.py (acousticFileList, used by
    create_nabat_file_list both to build a new list and to re-check access to an
    existing one)
Anything else (species sync) returns a GraphQL-shaped error rather than crashing,
so it's obvious a handler needs to be added rather than failing confusingly
downstream.

The combined query's response seeds one already-vetted species for every recording
fetched (see SEED_ANNOTATION_*), so create_nabat_recording_from_response() picks it
up and creates a matching NABatRecordingAnnotation automatically on first fetch -
giving you something to see immediately rather than an empty annotation list. This
requires a local Species row with a matching pk to already exist (the species-sync
query isn't mocked); most dev databases already have one from prior real usage.

Presigned URLs are generated for real against the `minio` service already in
docker-compose.yml, so the full download + spectrogram-generation pipeline
runs end-to-end against real infrastructure. Run upload_recording.py to seed
the object they point at (it also creates the bucket - this service never
needs a live connection to minio at all, since presigning is pure local
signing and does no network I/O).

Whoever downloads a presigned URL (the celery worker) needs to be able to
resolve the host baked into it, and that host must match what the URL was
signed with. Set MINIO_ENDPOINT accordingly: the compose-network name
`minio:9000` if celery also runs in Docker (the default), or `localhost:9000`
if celery runs natively on the host (see dev/.env.docker-compose-native),
since only the published port is reachable from there.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import re

from minio import Minio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nabat-mock")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioAccessKey")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioSecretKey")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "nabat-mock")
PORT = int(os.environ.get("PORT", "8082"))

# The single shared object every mocked recording_id resolves to. Per-ID fixture
# files aren't needed: any recording_id "just works" against this one object.
RECORDING_OBJECT_KEY = "recordings/example.wav"

# Reserved recording_id that always resolves to "not found", to exercise the
# existing 403 handling in get_email_if_authorized / generate_nabat_recording.
NOT_FOUND_RECORDING_ID = 0

# The "already vetted in NABat" species every newly-fetched recording seeds an
# annotation for. Must be a pk that actually exists in the local Species table
# (see the module docstring). Email matches dev/nabat_mock/NABAT-realm.json's test
# user, so the seeded annotation is visible when browsing as them.
SEED_ANNOTATION_SPECIES_ID = int(os.environ.get("SEED_ANNOTATION_SPECIES_ID", "1"))
SEED_ANNOTATION_EMAIL = os.environ.get("SEED_ANNOTATION_EMAIL", "testuser@example.com")

# nabat-mock's one file list, returned for any file_list_id - lists aren't per-id
# fixtures any more than recordings are. Item recording_ids start here, counting up
# (990000001, 990000002, ...) - deliberately a different range than the single-file
# flow's own default example (scripts/USGS/naBatInfo.py's 190255936), so testing the
# file-list flow fresh exercises actual materialization instead of instantly reusing
# a NABatRecording already created by testing the single-file flow.
FILE_LIST_ITEM_COUNT = int(os.environ.get("FILE_LIST_ITEM_COUNT", "10"))
FILE_LIST_FIRST_RECORDING_ID = 990000001
FILE_LIST_ITEM_SURVEY_EVENT_ID = 4768736

ACOUSTIC_FILE_ID_RE = re.compile(r'acousticFileId:\s*"?(\d+)"?')
ACOUSTIC_FILE_LIST_ID_RE = re.compile(r"acousticFileListById\(id:\s*(\d+)\)")

# Presigning is pure local signing - no network I/O - as long as a region is given
# (otherwise minio-py falls back to a live GetBucketLocation request). So this never
# actually needs to connect to minio; it just needs MINIO_ENDPOINT to be whatever host
# the downloader (celery) can resolve. See the module docstring.
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
    region="us-east-1",
)


def extract_id(pattern: re.Pattern, query: str) -> int | None:
    match = pattern.search(query)
    return int(match.group(1)) if match else None


def presigned_recording_url(recording_id: int) -> str | None:
    if recording_id == NOT_FOUND_RECORDING_ID:
        return None
    return minio_client.presigned_get_object(MINIO_BUCKET, RECORDING_OBJECT_KEY)


def build_presigned_only_response(query: str) -> dict:
    """Mirrors nabat_recording.py's QUERY: presignedUrlFromAcousticFile only."""
    recording_id = extract_id(ACOUSTIC_FILE_ID_RE, query)
    url = presigned_recording_url(recording_id) if recording_id is not None else None
    return {"data": {"presignedUrlFromAcousticFile": {"s3PresignedUrl": url} if url else None}}


def build_combined_response(query: str) -> dict:
    """Mirrors nabat_data_retrieval.py's fetchAcousticAndSurveyEventInfo query."""
    recording_id = extract_id(ACOUSTIC_FILE_ID_RE, query)
    url = presigned_recording_url(recording_id) if recording_id is not None else None

    return {
        "data": {
            "presignedUrlFromAcousticFile": {"s3PresignedUrl": url} if url else None,
            "surveyEventById": {
                "createdBy": "mock@nabat.org",
                "createdDate": "2024-01-01T00:00:00",
                "eventGeometryByEventGeometryId": {
                    "description": "Mock survey event geometry",
                    "geom": {"geojson": None},
                },
                "acousticBatchesBySurveyEventId": {
                    "nodes": [
                        {
                            "id": "mock-batch",
                            "acousticFileBatchesByBatchId": {
                                "nodes": [
                                    {
                                        "autoId": SEED_ANNOTATION_SPECIES_ID,
                                        "manualId": SEED_ANNOTATION_SPECIES_ID,
                                        "vetter": SEED_ANNOTATION_EMAIL,
                                        "speciesByManualId": None,
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
            "acousticFileById": {
                "fileName": f"mock_recording_{recording_id}.wav",
                "recordingTime": "2024-01-01T00:00:00",
                "s3Verified": True,
                "sizeBytes": 0,
            },
        }
    }


def build_update_vet_response(query: str) -> dict:
    """Mirrors nabat_recording.py's UPDATE_QUERY (updateAcousticFileVet mutation).

    Always succeeds. update_nabat_species only checks for an "errors" key, never
    reads the payload, so no fields here need to reflect what was actually sent.
    """
    return {"data": {"updateAcousticFileVet": {"acousticFileBatchId": 1}}}


def build_file_list_response(query: str) -> dict:
    """Mirrors nabat_file_list.py's QUERY (acousticFileList).

    Always returns the same FILE_LIST_ITEM_COUNT items, for any file_list_id - lists
    aren't per-id fixtures any more than recordings are. Every item resolves to the
    same underlying object (see presigned_recording_url) - distinct recording_ids,
    fileNames, and recordingTimes (5 minutes apart) are enough to exercise sorting
    and per-item status without needing distinct audio per file.
    """
    file_list_id = extract_id(ACOUSTIC_FILE_LIST_ID_RE, query)
    base_time = datetime(2024, 1, 1, tzinfo=UTC)
    nodes = []
    for i in range(FILE_LIST_ITEM_COUNT):
        recording_id = FILE_LIST_FIRST_RECORDING_ID + i
        recording_time = base_time + timedelta(minutes=5 * i)
        nodes.append(
            {
                "acousticFileByFileId": {
                    "id": str(recording_id),
                    "surveyEventId": FILE_LIST_ITEM_SURVEY_EVENT_ID,
                    "fileName": f"mock_recording_{recording_id}.wav",
                    "recordingTime": recording_time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            }
        )
    return {
        "data": {
            "acousticFileListById": {
                "name": f"mock_file_list_{file_list_id}.csv",
                "projectId": 1,
                "createdBy": SEED_ANNOTATION_EMAIL,
                "acousticFileAcousticFileListsByListId": {
                    "totalCount": len(nodes),
                    "nodes": nodes,
                },
            }
        }
    }


def build_response(query: str) -> dict:
    if "updateAcousticFileVet" in query:
        return build_update_vet_response(query)
    if "fetchAcousticAndSurveyEventInfo" in query:
        return build_combined_response(query)
    if "presignedUrlFromAcousticFile" in query:
        return build_presigned_only_response(query)
    if "acousticFileListById" in query:
        return build_file_list_response(query)
    return {"errors": [{"message": "nabat-mock has no handler for this query yet"}]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format_, *args):
        logger.info("%s - %s", self.address_string(), format_ % args)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            query = payload.get("query", "")
        except json.JSONDecodeError:
            query = ""

        response_body = json.dumps(build_response(query)).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)  # noqa: S104 (container-internal)
    logger.info("nabat-mock listening on :%s", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
