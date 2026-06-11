from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bats_ai.core.models import Annotations, Configuration

if TYPE_CHECKING:
    from bats_ai.core.models import Recording
    from bats_ai.core.utils.batbot_metadata import BatBotMetadataCurve

logger = logging.getLogger(__name__)

BATBOT_ANNOTATION_MODEL = "batbot"


def _segment_bounds(
    segment: BatBotMetadataCurve,
) -> tuple[float, float, float, float] | None:
    curve = segment.get("curve_hz_ms") or []
    if not curve:
        return None

    times = [pt[1] for pt in curve]
    freqs = [pt[0] for pt in curve]
    return min(times), max(times), min(freqs), max(freqs)


def create_pulse_annotations_from_batbot_segments(
    recording: Recording,
    segments: list[BatBotMetadataCurve],
) -> int:
    """Create pulse annotations from BatBot segments when enabled in Configuration."""
    config = Configuration.objects.first()
    if not config or not config.create_pulse_annotations_from_batbot:
        return 0

    Annotations.objects.filter(
        recording=recording,
        model=BATBOT_ANNOTATION_MODEL,
    ).delete()

    created = 0
    for segment in segments:
        bounds = _segment_bounds(segment)
        if bounds is None:
            segment_index = segment.get("segment_index")
            logger.warning(
                "Skipping BatBot pulse annotation for recording=%s segment_index=%s: no bbox",
                recording.pk,
                segment_index,
            )
            continue

        t_start, t_end, f_lo, f_hi = bounds
        Annotations.objects.create(
            recording=recording,
            owner=recording.owner,
            start_time=t_start,
            end_time=t_end,
            low_freq=f_lo,
            high_freq=f_hi,
            type="pulse",
            model=BATBOT_ANNOTATION_MODEL,
            comments="",
        )
        created += 1

    return created
