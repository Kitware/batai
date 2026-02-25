from __future__ import annotations

import logging
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING

from django.contrib.gis.geos import LineString, Point, Polygon
import requests

from bats_ai.core.models import ProcessingTask, PulseMetadata
from bats_ai.utils.spectrogram_utils import (
    generate_nabat_compressed_spectrogram,
    generate_nabat_spectrogram,
)

if TYPE_CHECKING:
    from bats_ai.core.models.nabat import NABatRecording

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NABatDataRetrieval")


def generate_spectrograms(
    self, nabat_recording: NABatRecording, presigned_url: str, processing_task: ProcessingTask
):
    from bats_ai.core.utils.batbot_metadata import generate_spectrogram_assets

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = None
        try:
            file_response = requests.get(presigned_url, stream=True, timeout=60)
            if file_response.status_code == 200:
                audio_file = Path(f"{tmpdir}/audio_file.wav")
                with open(audio_file, "wb") as temp_file:
                    temp_file.writelines(file_response.iter_content(chunk_size=8192))
        except Exception as e:
            logger.exception("Error Downloading Presigned URL")
            processing_task.status = ProcessingTask.Status.ERROR
            processing_task.error = f"Error Downloading Presigned URL: {e}"
            processing_task.save()
            raise

        # Generate spectrogram assets
        logger.info("Generating spectrograms...")
        self.update_state(
            state="Progress",
            meta={"description": "Generating Spectrograms"},
        )

        results = generate_spectrogram_assets(audio_file, tmpdir)

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
        for segment in compressed["contours"]["segments"]:
            pulse_metadata_obj, _ = PulseMetadata.objects.get_or_create(
                recording=compressed_obj.recording,
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
                PulseMetadata.objects.update_or_create(
                    recording=compressed_obj.recording,
                    index=segment["segment_index"],
                    defaults={
                        "curve": LineString([Point(x[1], x[0]) for x in segment["curve_hz_ms"]]),
                        "char_freq": Point(segment["char_freq_ms"], segment["char_freq_hz"]),
                        "knee": Point(segment["knee_ms"], segment["knee_hz"]),
                        "heel": Point(segment["heel_ms"], segment["heel_hz"]),
                    },
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
                pulse_metadata_obj.save()

        processing_task.status = ProcessingTask.Status.COMPLETE
        processing_task.save()
