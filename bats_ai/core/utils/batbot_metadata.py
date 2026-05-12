from __future__ import annotations

from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
from typing import Any, NotRequired, TypedDict

try:
    import batbot
except ImportError as exc:
    raise RuntimeError(
        "Spectrogram generation requires additional dependencies specified by the [tasks] extra."
    ) from exc

from django.conf import settings
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .contour_utils import process_spectrogram_assets_for_contours

logger = logging.getLogger(__name__)


class SpectrogramMetadata(BaseModel):
    """Metadata about BatBot spectrogram image outputs.

    BatBot 0.1.5 appends original-sample-rate images to the same path arrays as the
    default outputs when `include_original_sr=True`. Those files use the
    `.origsr.jpg` suffix and are split into dedicated `origsr` buckets by
    `generate_spectrogram_assets()`.
    """

    uncompressed_path: list[str] = Field(default_factory=list, alias="uncompressed.path")
    compressed_path: list[str] = Field(default_factory=list, alias="compressed.path")
    mask_path: list[str] = Field(default_factory=list, alias="mask.path")
    waveplot_path: list[str] = Field(default_factory=list, alias="waveplot.path")
    waveplot_compressed_path: list[str] = Field(
        default_factory=list,
        alias="waveplot.compressed.path",
    )


class ImageSize(BaseModel):
    """Image dimensions returned by BatBot."""

    width_px: int = Field(alias="width.px")
    height_px: int = Field(alias="height.px")


class SizeMetadata(BaseModel):
    """Size metadata for spectrograms."""

    uncompressed: ImageSize
    compressed: ImageSize
    compressed_origsr: ImageSize | None = None
    uncompressed_origsr: ImageSize | None = None


class FrequencyMetadata(BaseModel):
    """Frequency range metadata."""

    min_hz: int = Field(alias="min.hz")
    max_hz: int = Field(alias="max.hz")
    pixels_hz: list[int] = Field(alias="pixels.hz")


class OriginalSrMetadata(BaseModel):
    """Original-sample-rate metadata returned when `include_original_sr=True`."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    sr_hz: int = Field(alias="sr.hz")
    duration_ms: float = Field(alias="duration.ms")
    frequencies: FrequencyMetadata


class SegmentCurvePoint(BaseModel):
    """A single point in a segment curve."""

    frequency_hz: int
    time_ms: float


class Segment(BaseModel):
    """A detected segment in the spectrogram."""

    curve_hz_ms: list[list[float]] = Field(alias="curve.(hz,ms)")
    start_ms: float = Field(alias="segment start.ms")
    end_ms: float = Field(alias="segment end.ms")
    duration_ms: float = Field(alias="segment duration.ms")
    contour_start_ms: float = Field(alias="contour start.ms")
    contour_end_ms: float = Field(alias="contour end.ms")
    contour_duration_ms: float = Field(alias="contour duration.ms")
    threshold_amp: int = Field(alias="threshold.amp")
    peak_f_ms: float | None = Field(None, alias="peak f.ms")
    fc_ms: float | None = Field(None, alias="fc.ms")
    hi_fc_knee_ms: float | None = Field(None, alias="hi fc:knee.ms")
    lo_fc_heel_ms: float | None = Field(None, alias="lo fc:heel.ms")
    bandwidth_hz: int | None = Field(None, alias="bandwidth.hz")
    hi_f_hz: int | None = Field(None, alias="hi f.hz")
    lo_f_hz: int | None = Field(None, alias="lo f.hz")
    peak_f_hz: int | None = Field(None, alias="peak f.hz")
    fc_hz: int | None = Field(None, alias="fc.hz")
    hi_fc_knee_hz: int | None = Field(None, alias="hi fc:knee.hz")
    lo_fc_heel_hz: int | None = Field(None, alias="lo fc:heel.hz")
    harmonic_flag: bool = Field(False, alias="harmonic.flag")
    harmonic_peak_f_ms: float | None = Field(None, alias="harmonic peak f.ms")
    harmonic_peak_f_hz: int | None = Field(None, alias="harmonic peak f.hz")
    echo_flag: bool = Field(False, alias="echo.flag")
    echo_peak_f_ms: float | None = Field(None, alias="echo peak f.ms")
    echo_peak_f_hz: int | None = Field(None, alias="echo peak f.hz")
    # Slope fields (optional, many variations)
    slope_at_hi_fc_knee_khz_per_ms: float | None = Field(None, alias="slope@hi fc:knee.khz/ms")
    slope_at_fc_khz_per_ms: float | None = Field(None, alias="slope@fc.khz/ms")
    slope_at_low_fc_heel_khz_per_ms: float | None = Field(None, alias="slope@low fc:heel.khz/ms")
    slope_at_peak_khz_per_ms: float | None = Field(None, alias="slope@peak.khz/ms")
    slope_avg_khz_per_ms: float | None = Field(None, alias="slope[avg].khz/ms")
    slope_hi_avg_khz_per_ms: float | None = Field(None, alias="slope/hi[avg].khz/ms")
    slope_mid_avg_khz_per_ms: float | None = Field(None, alias="slope/mid[avg].khz/ms")
    slope_lo_avg_khz_per_ms: float | None = Field(None, alias="slope/lo[avg].khz/ms")
    slope_box_khz_per_ms: float | None = Field(None, alias="slope[box].khz/ms")
    slope_hi_box_khz_per_ms: float | None = Field(None, alias="slope/hi[box].khz/ms")
    slope_lo_box_khz_per_ms: float | None = Field(None, alias="slope/lo[box].khz/ms")

    @field_validator("curve_hz_ms", mode="before")
    @classmethod
    def validate_curve(cls, v: Any) -> list[list[float]]:
        """Ensure curve is a list of [frequency, time] pairs."""
        if isinstance(v, list):
            return v
        return []


class BatbotMetadata(BaseModel):
    """Complete BatBot metadata structure."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    wav_path: str = Field(alias="wav.path")
    spectrogram: SpectrogramMetadata
    global_threshold_amp: int = Field(alias="global_threshold.amp")
    sr_hz: int = Field(alias="sr.hz")
    duration_ms: float = Field(alias="duration.ms")
    frequencies: FrequencyMetadata
    size: SizeMetadata
    segments: list[Segment] = Field(default_factory=list)
    metadata_origsr: OriginalSrMetadata | None = None


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
        duration=round(metadata.duration_ms),
        frequency_min=metadata.frequencies.min_hz,
        frequency_max=metadata.frequencies.max_hz,
    )


def convert_to_compressed_spectrogram_data(
    metadata: BatbotMetadata,
    compressed_width: int | None = None,
) -> CompressedSpectrogramData:
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
    compressed_width = compressed_width or metadata.size.compressed.width_px
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


class SpectrogramAssetResult(TypedDict, total=False):
    paths: list[str]
    width: int
    height: int


class SpectrogramCompressedAssetResult(TypedDict, total=False):
    paths: list[str]
    masks: list[str]
    width: int
    height: int
    widths: list[float]
    starts: list[float]
    stops: list[float]


class SpectrogramContour(TypedDict):
    level: float
    curve: list[list[float]]
    index: int


class SpectrogramContourSegment(TypedDict):
    segment_index: int
    contour_count: int
    freq_min: float
    freq_max: float
    contours: list[SpectrogramContour]
    width_px: float
    start_ms: float
    stop_ms: float


class BatBotSlopes(TypedDict, total=False):
    """Slope values from batbot (kHz/ms). All keys optional."""

    slope_at_hi_fc_knee_khz_per_ms: float | None
    slope_at_fc_khz_per_ms: float | None
    slope_at_low_fc_heel_khz_per_ms: float | None
    slope_at_peak_khz_per_ms: float | None
    slope_avg_khz_per_ms: float | None
    slope_hi_avg_khz_per_ms: float | None
    slope_mid_avg_khz_per_ms: float | None
    slope_lo_avg_khz_per_ms: float | None
    slope_box_khz_per_ms: float | None
    slope_hi_box_khz_per_ms: float | None
    slope_lo_box_khz_per_ms: float | None


_SEGMENT_SLOPE_KEYS: tuple[str, ...] = (
    "slope_at_hi_fc_knee_khz_per_ms",
    "slope_at_fc_khz_per_ms",
    "slope_at_low_fc_heel_khz_per_ms",
    "slope_at_peak_khz_per_ms",
    "slope_avg_khz_per_ms",
    "slope_hi_avg_khz_per_ms",
    "slope_mid_avg_khz_per_ms",
    "slope_lo_avg_khz_per_ms",
    "slope_box_khz_per_ms",
    "slope_hi_box_khz_per_ms",
    "slope_lo_box_khz_per_ms",
)


class BatBotMetadataCurve(TypedDict):
    segment_index: int
    curve_hz_ms: list[float]
    char_freq_ms: float
    char_freq_hz: float
    knee_ms: float
    knee_hz: float
    heel_ms: float
    heel_hz: float
    bbox: list[float] | None
    slopes: NotRequired[BatBotSlopes]


class SpectrogramContours(TypedDict):
    segments: list[SpectrogramContourSegment]
    total_segments: int


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


def convert_to_segment_data(
    metadata: BatbotMetadata,
) -> list[BatBotMetadataCurve]:
    segment_data: list[BatBotMetadataCurve] = []
    for index, segment in enumerate(metadata.segments):
        slopes: BatBotSlopes = {}
        for key in _SEGMENT_SLOPE_KEYS:
            value = getattr(segment, key, None)
            if value is not None:
                slopes[key] = value

        bbox = [
            segment.start_ms,
            segment.end_ms,
            # Use min/max frequency if available, otherwise fallback to min.max for display
            segment.lo_f_hz if segment.lo_f_hz is not None else 5000,
            segment.hi_f_hz if segment.hi_f_hz is not None else 120000,
        ]
        segment_data_item: BatBotMetadataCurve = {
            "segment_index": index,
            "curve_hz_ms": segment.curve_hz_ms,
            "char_freq_ms": segment.fc_ms,
            "char_freq_hz": segment.fc_hz,
            "knee_ms": segment.hi_fc_knee_ms,
            "knee_hz": segment.hi_fc_knee_hz,
            "heel_ms": segment.lo_fc_heel_ms,
            "heel_hz": segment.lo_fc_heel_hz,
            "slopes": slopes,
            "bbox": bbox,
        }
        segment_data.append(segment_data_item)
    return segment_data


_ORIGSR_SUFFIX = ".origsr.jpg"


def _split_origsr_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    """Split BatBot path arrays into default and original-sample-rate files."""
    default_paths: list[str] = []
    origsr_paths: list[str] = []
    for path in paths:
        if path.endswith(_ORIGSR_SUFFIX):
            origsr_paths.append(path)
        else:
            default_paths.append(path)
    return default_paths, origsr_paths


def _build_original_sr_metadata_result(
    metadata: OriginalSrMetadata | None,
) -> dict[str, Any] | None:
    if metadata is None:
        return None

    return metadata.model_dump(by_alias=True)


def _build_normal_origsr_asset_result(
    *,
    paths: list[str],
    waveplot_paths: list[str],
    size: ImageSize | None,
) -> SpectrogramAssetResult | None:
    result: SpectrogramAssetResult = {}
    if paths:
        result["paths"] = paths
    if waveplot_paths:
        result["waveplot_paths"] = waveplot_paths
    if size is not None:
        result["width"] = size.width_px
        result["height"] = size.height_px
    return result or None


def _build_compressed_origsr_asset_result(
    *,
    metadata: BatbotMetadata,
    path_overrides: dict[str, list[str]],
    size: SizeMetadata,
) -> SpectrogramCompressedAssetResult | None:
    result: SpectrogramCompressedAssetResult = {}
    if path_overrides.get("paths"):
        result["paths"] = path_overrides["paths"]
    if path_overrides.get("masks"):
        result["masks"] = path_overrides["masks"]
    if path_overrides.get("masked_paths"):
        result["masked_paths"] = path_overrides["masked_paths"]
    if path_overrides.get("waveplot_paths"):
        result["waveplot_paths"] = path_overrides["waveplot_paths"]
    if size.compressed_origsr is not None:
        result["width"] = size.compressed_origsr.width_px
        result["height"] = size.compressed_origsr.height_px
        if size.compressed_origsr.width_px != size.compressed.width_px:
            compressed_metadata = convert_to_compressed_spectrogram_data(
                metadata,
                compressed_width=size.compressed_origsr.width_px,
            )
            result["widths"] = compressed_metadata.widths
    if size.mask_origsr is not None:
        result["mask_size"] = {
            "width": size.mask_origsr.width_px,
            "height": size.mask_origsr.height_px,
        }
    if size.masked_origsr is not None:
        result["masked_size"] = {
            "width": size.masked_origsr.width_px,
            "height": size.masked_origsr.height_px,
        }
    return result or None


def _promote_original_sr_assets(result: SpectrogramAssets) -> None:
    normal_origsr = result["normal"].get("origsr")
    if normal_origsr:
        result["normal"].update(normal_origsr)

    compressed_origsr = result["compressed"].get("origsr")
    if compressed_origsr:
        result["compressed"].update(compressed_origsr)

    metadata_origsr = result.get("metadata_origsr")
    if not isinstance(metadata_origsr, dict):
        return

    duration_ms = metadata_origsr.get("duration.ms")
    if isinstance(duration_ms, (int, float)):
        result["duration"] = float(duration_ms)

    frequencies = metadata_origsr.get("frequencies")
    if not isinstance(frequencies, dict):
        return

    min_hz = frequencies.get("min.hz")
    if isinstance(min_hz, int):
        result["freq_min"] = min_hz

    max_hz = frequencies.get("max.hz")
    if isinstance(max_hz, int):
        result["freq_max"] = max_hz


def generate_spectrogram_assets(
    recording_path: str,
    output_folder: str,
    *,
    use_original_sr: bool = False,
) -> SpectrogramAssets:
    """Generate spectrogram assets from BatBot metadata.

    When `include_original_sr=True`, BatBot 0.1.5 writes additional
    `.origsr.jpg` files into the same metadata path arrays as the default assets.
    This wrapper separates those files into dedicated `origsr` result buckets.
    When `use_original_sr=True`, those override values are promoted into the main
    `normal` and `compressed` results before returning.
    """
    include_original_sr = False
    if use_original_sr:
        include_original_sr = True

    pipeline_kwargs: dict[str, Any] = {
        "output_folder": output_folder,
        "quiet": True,
    }
    if include_original_sr:
        pipeline_kwargs["include_original_sr"] = True

    batbot.pipeline(recording_path, **pipeline_kwargs)
    # There should be a .metadata.json file in the output_base directory by replacing extentions
    metadata_file = Path(recording_path).with_suffix(".metadata.json").name
    metadata_file = Path(output_folder) / metadata_file
    metadata = parse_batbot_metadata(metadata_file)
    # from the metadata we should have the images that are used
    uncompressed_paths, uncompressed_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.uncompressed_path
    )
    compressed_paths, compressed_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.compressed_path
    )
    mask_paths, mask_origsr_paths = _split_origsr_paths(metadata.spectrogram.mask_path)
    masked_paths, masked_origsr_paths = _split_origsr_paths(metadata.spectrogram.masked_path)
    waveplot_paths, waveplot_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.waveplot_path
    )
    compressed_waveplot_paths, compressed_waveplot_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.waveplot_compressed_path
    )

    compressed_metadata = convert_to_compressed_spectrogram_data(metadata)
    segment_curve_data = convert_to_segment_data(metadata)
    result: SpectrogramAssets = {
        "duration": metadata.duration_ms,
        "freq_min": metadata.frequencies.min_hz,
        "freq_max": metadata.frequencies.max_hz,
        "normal": {
            "paths": uncompressed_paths,
            "waveplot_paths": waveplot_paths,
            "width": metadata.size.uncompressed.width_px,
            "height": metadata.size.uncompressed.height_px,
        },
        "compressed": {
            "paths": compressed_paths,
            "masks": mask_paths,
            "masked_paths": masked_paths,
            "waveplot_paths": compressed_waveplot_paths,
            "width": metadata.size.compressed.width_px,
            "height": metadata.size.compressed.height_px,
            "widths": compressed_metadata.widths,
            "starts": compressed_metadata.starts,
            "stops": compressed_metadata.stops,
            "segments": segment_curve_data,
        },
    }

    normal_origsr = _build_normal_origsr_asset_result(
        paths=uncompressed_origsr_paths,
        waveplot_paths=waveplot_origsr_paths,
        size=metadata.size.uncompressed_origsr,
    )
    if normal_origsr:
        result["normal"]["origsr"] = normal_origsr

    compressed_origsr = _build_compressed_origsr_asset_result(
        metadata=metadata,
        path_overrides={
            "paths": compressed_origsr_paths,
            "masks": mask_origsr_paths,
            "masked_paths": masked_origsr_paths,
            "waveplot_paths": compressed_waveplot_origsr_paths,
        },
        size=metadata.size,
    )
    if compressed_origsr:
        result["compressed"]["origsr"] = compressed_origsr

    original_sr_metadata = _build_original_sr_metadata_result(metadata.metadata_origsr)
    if original_sr_metadata is not None:
        result["metadata_origsr"] = original_sr_metadata

    if use_original_sr:
        _promote_original_sr_assets(result)

    if settings.BATAI_SAVE_SPECTROGRAM_CONTOURS:
        result["compressed"]["contours"] = process_spectrogram_assets_for_contours(result)
    else:
        result["compressed"]["contours"] = {"segments": [], "total_segments": 0}

    return result
