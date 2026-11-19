"""Expected, explainable failures raised by BatAI background tasks.

`str()` of any `ProcessingTaskError` is written to `ProcessingTask.error`, which is
exposed through the API - so messages must be safe to show to users (no tokens,
presigned URLs, or tracebacks). Wrap lower-level exceptions with `raise ... from e`
so the full cause still reaches logs and Sentry.

Constructors take a single message argument: Celery serializes exceptions into the
result backend and rebuilds them from their args, so extra required constructor
arguments would break that round trip.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar


class FailureCode(StrEnum):
    """Machine-readable reason a ProcessingTask failed.

    Stored as `failureCode` in `ProcessingTask.output_metadata` alongside the
    human-readable `ProcessingTask.error`, so code can act on the kind of failure
    without parsing messages.
    """

    NABAT_REQUEST = "nabat_request"
    NABAT_AUTH = "nabat_auth"
    NABAT_INVALID_RESPONSE = "nabat_invalid_response"
    NABAT_GRAPHQL = "nabat_graphql"
    NABAT_MISSING_DATA = "nabat_missing_data"
    RECORDING_DOWNLOAD = "recording_download"
    SPECTROGRAM_GENERATION = "spectrogram_generation"
    # The task ran past its soft time limit.
    TIME_LIMIT = "time_limit"
    # The task stopped without reporting a result, e.g. the worker was killed.
    WORKER_LOST = "worker_lost"
    # The task waited in the queue past its expiry without a worker starting it.
    QUEUE_TIMEOUT = "queue_timeout"
    # The task couldn't be sent to the broker.
    DISPATCH_FAILED = "dispatch_failed"
    # Any exception that isn't a ProcessingTaskError.
    UNEXPECTED = "unexpected"


class ProcessingTaskError(Exception):
    """Base class for failures whose message is safe to store on a ProcessingTask."""

    code: ClassVar[FailureCode] = FailureCode.UNEXPECTED


class NABatRequestError(ProcessingTaskError):
    """The NABat API couldn't be reached, timed out, or returned a non-200 response."""

    code = FailureCode.NABAT_REQUEST


class NABatAuthError(NABatRequestError):
    """NABat rejected the request's credentials (HTTP 401/403)."""

    code = FailureCode.NABAT_AUTH


class NABatInvalidResponseError(ProcessingTaskError):
    """NABat returned a 200 response whose body wasn't valid JSON."""

    code = FailureCode.NABAT_INVALID_RESPONSE


class NABatGraphQLError(ProcessingTaskError):
    """NABat's GraphQL response included an `errors` list."""

    code = FailureCode.NABAT_GRAPHQL


class NABatMissingDataError(ProcessingTaskError):
    """A required field in NABat's response was null or absent, with no GraphQL errors.

    NABat can return null for rows the caller isn't permitted to see, so this can't
    distinguish "doesn't exist" from "no access".
    """

    code = FailureCode.NABAT_MISSING_DATA


class RecordingDownloadError(ProcessingTaskError):
    """The recording's audio file couldn't be downloaded from its presigned URL."""

    code = FailureCode.RECORDING_DOWNLOAD


class SpectrogramGenerationError(ProcessingTaskError):
    """Spectrogram generation failed, or its output couldn't be converted to models."""

    code = FailureCode.SPECTROGRAM_GENERATION
