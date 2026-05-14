from __future__ import annotations

from django.db.models import Case, F, IntegerField, Value, When


def recording_effective_sample_frame_id_case() -> Case:
    """Return a ``Case`` matching ``normalize_sample_frame_id`` for ``Recording`` rows."""
    return Case(
        When(sample_frame_id__isnull=True, then=Value(14)),
        When(sample_frame_id=19, then=Value(20)),
        default=F("sample_frame_id"),
        output_field=IntegerField(),
    )


def normalize_sample_frame_id(sample_frame_id: int | None) -> int | None:
    """Normalize sample frame IDs for AKCAN compatibility.

    The current AKCAN source shapefile contains a combined Alaska/Canada
    frame and
    does not expose an attribute that allows us to split rows into distinct 19
    (Canada) and 20 (Alaska) subsets. Until separate sources are available,
    treat incoming 19 as 20 so legacy callers continue to resolve cells.
    """
    if sample_frame_id == 19:
        return 20
    if sample_frame_id is None:
        return 14
    return sample_frame_id
