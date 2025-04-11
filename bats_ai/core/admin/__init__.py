from .annotations import AnnotationsAdmin
from .compressed_spectrogram import CompressedSpectrogramAdmin
from .configuration import ConfigurationAdmin
from .grts_cells import GRTSCellsAdmin
from .image import ImageAdmin
from .nabat.admin import (
    NABatCompressedSpectrogram,
    NABatRecording,
    NABatRecordingAnnotation,
    NABatSpectrogram,
)
from .processing_task import ProcessingTaskAdmin
from .recording import RecordingAdmin
from .recording_annotations import RecordingAnnotationAdmin
from .species import SpeciesAdmin
from .spectrogram import SpectrogramAdmin
from .temporal_annotations import TemporalAnnotationsAdmin

__all__ = [
    'AnnotationsAdmin',
    'ImageAdmin',
    'RecordingAdmin',
    'SpectrogramAdmin',
    'TemporalAnnotationsAdmin',
    'SpeciesAdmin',
    'GRTSCellsAdmin',
    'CompressedSpectrogramAdmin',
    'RecordingAnnotationAdmin',
    'ProcessingTaskAdmin',
    'ConfigurationAdmin',
    # NABat Models
    'NABatRecordingAnnotation',
    'NABatCompressedSpectrogram',
    'NABatSpectrogram',
    'NABatRecording',
]
