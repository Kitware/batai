from .annotations import AnnotationsAdmin
from .compressed_spectrogram import CompressedSpectrogramAdmin
from .configuration import ConfigurationAdmin
from .exported_annotation import ExportedAnnotationFileAdmin
from .grts_cells import GRTSCellsAdmin
from .image import ImageAdmin
from .nabat.admin import (
    NABatCompressedSpectrogramAdmin,
    NABatRecordingAdmin,
    NABatRecordingAnnotationAdmin,
    NABatSpectrogramAdmin,
)
from .processing_task import ProcessingTaskAdmin
from .recording import RecordingAdmin
from .recording_annotations import RecordingAnnotationAdmin
from .recording_tag import RecordingTagAdmin
from .sequence_annotations import SequenceAnnotationsAdmin
from .species import SpeciesAdmin
from .spectrogram import SpectrogramAdmin
from .spectrogram_image import SpectrogramImageAdmin
from .spectrogram_svg import SpectrogramSvgAdmin

__all__ = [
    'AnnotationsAdmin',
    'ImageAdmin',
    'RecordingAdmin',
    'SpectrogramAdmin',
    'SequenceAnnotationsAdmin',
    'SpeciesAdmin',
    'GRTSCellsAdmin',
    'CompressedSpectrogramAdmin',
    'RecordingAnnotationAdmin',
    'RecordingTagAdmin',
    'ProcessingTaskAdmin',
    'ConfigurationAdmin',
    'ExportedAnnotationFileAdmin',
    'SpectrogramImageAdmin',
    'SpectrogramSvgAdmin',
    # NABat Models
    'NABatRecordingAnnotationAdmin',
    'NABatCompressedSpectrogramAdmin',
    'NABatSpectrogramAdmin',
    'NABatRecordingAdmin',
]
