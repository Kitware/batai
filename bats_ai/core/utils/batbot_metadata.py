from contextlib import contextmanager
import json
import os
from pathlib import Path
from typing import Any, TypedDict

import batbot
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpectrogramMetadata(BaseModel):
    """Metadata about the spectrogram."""

    uncompressed_path: list[str] = Field(alias='uncompressed.path')
    compressed_path: list[str] = Field(alias='compressed.path')


class UncompressedSize(BaseModel):
    """Uncompressed spectrogram dimensions."""

    width_px: int = Field(alias='width.px')
    height_px: int = Field(alias='height.px')


class CompressedSize(BaseModel):
    """Compressed spectrogram dimensions."""

    width_px: int = Field(alias='width.px')
    height_px: int = Field(alias='height.px')


class SizeMetadata(BaseModel):
    """Size metadata for spectrograms."""

    uncompressed: UncompressedSize
    compressed: CompressedSize


class FrequencyMetadata(BaseModel):
    """Frequency range metadata."""

    min_hz: int = Field(alias='min.hz')
    max_hz: int = Field(alias='max.hz')
    pixels_hz: list[int] = Field(alias='pixels.hz')


class SegmentCurvePoint(BaseModel):
    """A single point in a segment curve."""

    frequency_hz: int
    time_ms: float


class Segment(BaseModel):
    """A detected segment in the spectrogram."""

    curve_hz_ms: list[list[float]] = Field(alias='curve.(hz,ms)')
    start_ms: float = Field(alias='start.ms')
    end_ms: float = Field(alias='end.ms')
    duration_ms: float = Field(alias='duration.ms')
    threshold_amp: int = Field(alias='threshold.amp')
    peak_f_ms: float | None = Field(None, alias='peak f.ms')
    fc_ms: float | None = Field(None, alias='fc.ms')
    hi_fc_knee_ms: float | None = Field(None, alias='hi fc:knee.ms')
    lo_fc_heel_ms: float | None = Field(None, alias='lo fc:heel.ms')
    bandwidth_hz: int | None = Field(None, alias='bandwidth.hz')
    hi_f_hz: int | None = Field(None, alias='hi f.hz')
    lo_f_hz: int | None = Field(None, alias='lo f.hz')
    peak_f_hz: int | None = Field(None, alias='peak f.hz')
    fc_hz: int | None = Field(None, alias='fc.hz')
    hi_fc_knee_hz: int | None = Field(None, alias='hi fc:knee.hz')
    lo_fc_heel_hz: int | None = Field(None, alias='lo fc:heel.hz')
    harmonic_flag: bool = Field(False, alias='harmonic.flag')
    harmonic_peak_f_ms: float | None = Field(None, alias='harmonic peak f.ms')
    harmonic_peak_f_hz: int | None = Field(None, alias='harmonic peak f.hz')
    echo_flag: bool = Field(False, alias='echo.flag')
    echo_peak_f_ms: float | None = Field(None, alias='echo peak f.ms')
    echo_peak_f_hz: int | None = Field(None, alias='echo peak f.hz')
    # Slope fields (optional, many variations)
    slope_at_hi_fc_knee_khz_per_ms: float | None = Field(None, alias='slope@hi fc:knee.khz/ms')
    slope_at_fc_khz_per_ms: float | None = Field(None, alias='slope@fc.khz/ms')
    slope_at_low_fc_heel_khz_per_ms: float | None = Field(None, alias='slope@low fc:heel.khz/ms')
    slope_at_peak_khz_per_ms: float | None = Field(None, alias='slope@peak.khz/ms')
    slope_avg_khz_per_ms: float | None = Field(None, alias='slope[avg].khz/ms')
    slope_hi_avg_khz_per_ms: float | None = Field(None, alias='slope/hi[avg].khz/ms')
    slope_mid_avg_khz_per_ms: float | None = Field(None, alias='slope/mid[avg].khz/ms')
    slope_lo_avg_khz_per_ms: float | None = Field(None, alias='slope/lo[avg].khz/ms')
    slope_box_khz_per_ms: float | None = Field(None, alias='slope[box].khz/ms')
    slope_hi_box_khz_per_ms: float | None = Field(None, alias='slope/hi[box].khz/ms')
    slope_mid_box_khz_per_ms: float | None = Field(None, alias='slope/mid[box].khz/ms')
    slope_lo_box_khz_per_ms: float | None = Field(None, alias='slope/lo[box].khz/ms')

    @field_validator('curve_hz_ms', mode='before')
    @classmethod
    def validate_curve(cls, v: Any) -> list[list[float]]:
        """Ensure curve is a list of [frequency, time] pairs."""
        if isinstance(v, list):
            return v
        return []


class BatbotMetadata(BaseModel):
    """Complete BatBot metadata structure."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    wav_path: str = Field(alias='wav.path')
    spectrogram: SpectrogramMetadata
    global_threshold_amp: int = Field(alias='global_threshold.amp')
    sr_hz: int = Field(alias='sr.hz')
    duration_ms: float = Field(alias='duration.ms')
    frequencies: FrequencyMetadata
    size: SizeMetadata
    segments: list[Segment]


class SpectrogramData(BaseModel):
    """Data structure for creating a Spectrogram model."""

    width: int
    height: int
    duration: int  # milliseconds
    frequency_min: int  # hz
    frequency_max: int  # hz


class CompressedSpectrogramData(BaseModel):
    """Data structure for creating a CompressedSpectrogram model."""

    starts: list[float]
    stops: list[float]
    widths: list[float]


def parse_batbot_metadata(file_path: str | Path) -> BatbotMetadata:
    """Parse a BatBot metadata JSON file.

    Args:
        file_path: Path to the metadata JSON file

    Returns:
        Parsed BatbotMetadata object
    """
    file_path = Path(file_path)
    with open(file_path) as f:
        data = json.load(f)
    return BatbotMetadata(**data)


def convert_to_spectrogram_data(metadata: BatbotMetadata) -> SpectrogramData:
    """Convert BatBot metadata to Spectrogram model data.

    Args:
        metadata: Parsed BatBot metadata

    Returns:
        SpectrogramData with fields for Spectrogram model
    """
    return SpectrogramData(
        width=metadata.size.uncompressed.width_px,
        height=metadata.size.uncompressed.height_px,
        duration=int(round(metadata.duration_ms)),
        frequency_min=metadata.frequencies.min_hz,
        frequency_max=metadata.frequencies.max_hz,
    )


def convert_to_compressed_spectrogram_data(metadata: BatbotMetadata) -> CompressedSpectrogramData:
    """Convert BatBot metadata to CompressedSpectrogram model data.

    This function calculates starts, stops, and widths for each compressed image
    based on the segments and the relationship between uncompressed and compressed widths.

    The compressed image is a concatenation of segments from the uncompressed image.
    - starts/stops: time values in milliseconds (matching the pattern in spectrogram_utils.py)
    - widths: pixel widths in the compressed image (where segments are concatenated)

    Args:
        metadata: Parsed BatBot metadata

    Returns:
        CompressedSpectrogramData with fields for CompressedSpectrogram model
    """
    duration_ms = metadata.duration_ms

    # Process each compressed image
    starts_ms: list[int] = []
    stops_ms: list[int] = []
    widths_px_compressed: list[int] = []
    segment_times: list[int] = []
    compressed_width = metadata.size.compressed.width_px
    total_time = 0.0

    # If we have segments, use them to determine which parts are kept
    if metadata.segments:
        for segment in metadata.segments:
            starts_ms.append(segment.start_ms)
            stops_ms.append(segment.end_ms)
            time = segment.end_ms - segment.start_ms
            segment_times.append(time)
            total_time += time
            # Calculate width in compressed space
            # The width in compressed space is proportional to the time duration
        for time in segment_times:
            width_px = (time / total_time) * compressed_width
            widths_px_compressed.append(width_px)
    else:
        # No segments - the entire image is compressed
        starts_ms = [0]
        stops_ms = [duration_ms]
        widths_px_compressed = [compressed_width]

    return CompressedSpectrogramData(
        starts=starts_ms,
        stops=stops_ms,
        widths=widths_px_compressed,
    )


class SpectrogramAssetResult(TypedDict):
    paths: list[str]
    width: int
    height: int


class SpectrogramCompressedAssetResult(TypedDict):
    paths: list[str]
    width: int
    height: int
    widths: list[float]
    starts: list[float]
    stops: list[float]


class SpectrogramAssets(TypedDict):
    duration: float
    freq_min: int
    freq_max: int
    normal: SpectrogramAssetResult
    compressed: SpectrogramCompressedAssetResult


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def generate_spectrogram_assets(recording_path: str, output_folder: str):
    batbot.pipeline(recording_path, config=None, output_folder=output_folder)
    # There should be a .metadata.json file in the output_base directory by replacing extentions
    metadata_file = Path(recording_path).with_suffix('.metadata.json').name
    metadata_file = Path(output_folder) / metadata_file
    metadata = parse_batbot_metadata(metadata_file)
    # from the metadata we should have the images that are used
    uncompressed_paths = metadata.spectrogram.uncompressed_path
    compressed_paths = metadata.spectrogram.compressed_path

    metadata.frequencies.min_hz
    metadata.frequencies.max_hz

    compressed_metadata = convert_to_compressed_spectrogram_data(metadata)
    result = {
        'duration': metadata.duration_ms,
        'freq_min': metadata.frequencies.min_hz,
        'freq_max': metadata.frequencies.max_hz,
        'normal': {
            'paths': uncompressed_paths,
            'width': metadata.size.uncompressed.width_px,
            'height': metadata.size.uncompressed.height_px,
        },
        'compressed': {
            'paths': compressed_paths,
            'width': metadata.size.compressed.width_px,
            'height': metadata.size.compressed.height_px,
            'widths': compressed_metadata.widths,
            'starts': compressed_metadata.starts,
            'stops': compressed_metadata.stops,
        },
    }
    return result
