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


class ProcessingTaskError(Exception):
    """Base class for failures whose message is safe to store on a ProcessingTask."""


class NABatRequestError(ProcessingTaskError):
    """The NABat API couldn't be reached, timed out, or returned a non-200 response."""


class NABatAuthError(NABatRequestError):
    """NABat rejected the request's credentials (HTTP 401/403)."""


class NABatInvalidResponseError(ProcessingTaskError):
    """NABat returned a 200 response whose body wasn't valid JSON."""


class NABatGraphQLError(ProcessingTaskError):
    """NABat's GraphQL response included an `errors` list."""


class NABatMissingDataError(ProcessingTaskError):
    """A required field in NABat's response was null or absent, with no GraphQL errors.

    NABat can return null for rows the caller isn't permitted to see, so this can't
    distinguish "doesn't exist" from "no access".
    """


class RecordingDownloadError(ProcessingTaskError):
    """The recording's audio file couldn't be downloaded from its presigned URL."""


class SpectrogramGenerationError(ProcessingTaskError):
    """Spectrogram generation failed, or its output couldn't be converted to models."""
