from __future__ import annotations

import logging
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.contrib.gis.geos import LineString, Point, Polygon
import requests

from bats_ai.core.errors import RecordingDownloadError, SpectrogramGenerationError
from bats_ai.core.models import ProcessingTask
from bats_ai.core.models.nabat import NABatPulseMetadata
from bats_ai.utils.spectrogram_utils import (
    generate_nabat_compressed_spectrogram,
    generate_nabat_spectrogram,
)

if TYPE_CHECKING:
    from bats_ai.core.models.nabat import NABatRecording

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NABatDataRetrieval")


def generate_spectrograms(  # noqa: C901, PLR0912, PLR0915
    self, nabat_recording: NABatRecording, presigned_url: str, processing_task: ProcessingTask
):
    from bats_ai.core.utils.batbot_metadata import generate_spectrogram_assets

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = Path(f"{tmpdir}/audio_file.wav")
        try:
            file_response = requests.get(presigned_url, stream=True, timeout=60)
            file_response.raise_for_status()
            with open(audio_file, "wb") as temp_file:
                temp_file.writelines(file_response.iter_content(chunk_size=8192))
        except requests.HTTPError as e:
            raise RecordingDownloadError(
                f"Could not download the recording file (HTTP {e.response.status_code})"
            ) from e
        except requests.RequestException as e:
            raise RecordingDownloadError(
                f"Could not download the recording file: {type(e).__name__}"
            ) from e

        # Generate spectrogram assets
        logger.info("Generating spectrograms...")
        self.update_state(
            state="Progress",
            meta={"description": "Generating Spectrograms"},
        )

        try:
            results = generate_spectrogram_assets(str(audio_file), tmpdir)
        except SoftTimeLimitExceeded:
            # Let the task's time limit be reported as such, not as a BatBot failure.
            raise
        except Exception as e:
            raise SpectrogramGenerationError(
                f"Spectrogram generation failed: {type(e).__name__}"
            ) from e

        self.update_state(
            state="Progress",
            meta={"description": "Converting Spectrograms to Models"},
        )

        spectrogram = generate_nabat_spectrogram(nabat_recording, results)

        compressed = results["compressed"]

        compressed_obj = generate_nabat_compressed_spectrogram(
            nabat_recording, spectrogram, compressed
        )
        segment_index_map = {}
        contour_segments = compressed.get("contours", {}).get("segments", [])
        for segment in contour_segments:
            pulse_metadata_obj, _ = NABatPulseMetadata.objects.get_or_create(
                nabat_recording=compressed_obj.nabat_recording,
                index=segment["segment_index"],
                defaults={
                    "contours": segment["contours"],
                    "bounding_box": Polygon(
                        (
                            (segment["start_ms"], segment["freq_max"]),
                            (segment["stop_ms"], segment["freq_max"]),
                            (segment["stop_ms"], segment["freq_min"]),
                            (segment["start_ms"], segment["freq_min"]),
                            (segment["start_ms"], segment["freq_max"]),
                        )
                    ),
                },
            )
            segment_index_map[segment["segment_index"]] = pulse_metadata_obj
        for segment in compressed["segments"]:
            if segment["segment_index"] not in segment_index_map:
                defaults = {
                    "curve": LineString([Point(x[1], x[0]) for x in segment["curve_hz_ms"]]),
                    "char_freq": Point(segment["char_freq_ms"], segment["char_freq_hz"]),
                    "knee": Point(segment["knee_ms"], segment["knee_hz"]),
                    "heel": Point(segment["heel_ms"], segment["heel_hz"]),
                    "slopes": segment.get("slopes"),
                }
                # `NABatPulseMetadata.bounding_box` is non-nullable, so always populate it
                # for rows not created from `compressed["contours"]`.
                segment_bbox = segment.get("bbox")
                if segment_bbox and len(segment_bbox) == 4:
                    t_start, t_end, f_lo, f_hi = segment_bbox
                else:
                    # Fallback: derive bounds from curve points.
                    curve = segment.get("curve_hz_ms") or []
                    if not curve:
                        segment_index = segment.get("segment_index")
                        raise SpectrogramGenerationError(
                            f"Missing bbox and curve_hz_ms for segment_index={segment_index}"
                        )
                    times = [pt[1] for pt in curve]
                    freqs = [pt[0] for pt in curve]
                    t_start, t_end = min(times), max(times)
                    f_lo, f_hi = min(freqs), max(freqs)
                defaults["bounding_box"] = Polygon(
                    (
                        (t_start, f_hi),
                        (t_end, f_hi),
                        (t_end, f_lo),
                        (t_start, f_lo),
                        (t_start, f_hi),
                    )
                )
                if not settings.BATAI_SAVE_SPECTROGRAM_CONTOURS:
                    defaults["contours"] = []

                NABatPulseMetadata.objects.update_or_create(
                    nabat_recording=compressed_obj.nabat_recording,
                    index=segment["segment_index"],
                    defaults=defaults,
                )
            else:
                pulse_metadata_obj = segment_index_map[segment["segment_index"]]
                pulse_metadata_obj.curve = LineString(
                    [Point(x[1], x[0]) for x in segment["curve_hz_ms"]]
                )
                pulse_metadata_obj.char_freq = Point(
                    segment["char_freq_ms"], segment["char_freq_hz"]
                )
                pulse_metadata_obj.knee = Point(segment["knee_ms"], segment["knee_hz"])
                pulse_metadata_obj.heel = Point(segment["heel_ms"], segment["heel_hz"])
                slopes = segment.get("slopes")
                if slopes:
                    pulse_metadata_obj.slopes = slopes
                if not settings.BATAI_SAVE_SPECTROGRAM_CONTOURS:
                    pulse_metadata_obj.contours = []
                pulse_metadata_obj.save()

        processing_task.status = ProcessingTask.Status.COMPLETE
        processing_task.save()
