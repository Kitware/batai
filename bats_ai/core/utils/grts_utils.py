from __future__ import annotations


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
    return sample_frame_id
