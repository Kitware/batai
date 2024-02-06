from .annotations import router as AnnotationRouter
from .recording import router as RecordingRouter
from .species import router as SpeciesRouter
from .temporal_annotations import router as TemporalAnnotationRouter

__all__ = [
    'RecordingRouter',
    'SpeciesRouter',
    'AnnotationRouter',
    'TemporalAnnotationRouter',
]
