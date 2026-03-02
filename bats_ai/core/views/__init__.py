from __future__ import annotations

from .annotations import router as annotation_router
from .configuration import router as configuration_router
from .export_annotation import router as export_annotation_router
from .grts_cells import router as grts_cells_router
from .guanometadata import router as guano_metadata_router
from .processing_tasks import router as processing_task_router
from .recording import router as recording_router
from .recording_annotation import router as recording_annotation_router
from .recording_tag import router as recording_tag_router
from .sequence_annotations import router as sequence_annotation_router
from .species import router as species_router
from .vetting_details import router as vetting_router

__all__ = [
    "annotation_router",
    "configuration_router",
    "export_annotation_router",
    "grts_cells_router",
    "guano_metadata_router",
    "processing_task_router",
    "recording_annotation_router",
    "recording_router",
    "recording_tag_router",
    "sequence_annotation_router",
    "species_router",
    "vetting_router",
]
