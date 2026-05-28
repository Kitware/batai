# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "batbot==0.1.5",
#     "click",
#     "pydantic",
# ]
#
# ///
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from os.path import exists
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import batbot
from batbot import log
import click
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Set to True to promote .origsr.jpg assets into the main normal/compressed buckets
# in the output JSON.
USE_ORIGINAL_SR_SPECTROGRAMS = False


class SpectrogramMetadata(BaseModel):
    """Metadata about BatBot spectrogram image outputs.

    BatBot appends original-sample-rate images to the same path arrays as the
    default outputs when `include_original_sr=True`. Those files use the
    `.origsr.jpg` suffix and are split into dedicated `origsr` buckets by
    `generate_spectrogram_assets()`.

    BatBot also writes ``masked.path`` (``*.masked.jpg``): the compressed spectrogram
    multiplied by segmentation weights. This script ignores those paths. Use
    ``mask.path`` (``*.mask.jpg``) only — the cost/weight image for contours.
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
    mask_origsr: ImageSize | None = None


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
    starts_ms: list[float] = []
    stops_ms: list[float] = []
    widths_px_compressed: list[float] = []
    segment_times: list[float] = []
    compressed_width = compressed_width or metadata.size.compressed.width_px
    total_time = 0.0

    # If we have segments, use them to determine which parts are kept
    if metadata.segments:
        for segment in metadata.segments:
            starts_ms.append(segment.start_ms)
            stops_ms.append(segment.end_ms)
            time = round(segment.end_ms) - round(segment.start_ms)
            segment_times.append(time)
            total_time += time
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
    waveplots: list[str]
    width: int
    height: int
    widths: list[float]
    origsr: NotRequired[SpectrogramAssetResult]


class SpectrogramCompressedAssetResult(TypedDict, total=False):
    paths: list[str]
    masks: list[str]
    waveplots: list[str]
    width: int
    height: int
    widths: list[float]
    starts: list[float]
    stops: list[float]
    mask_size: NotRequired[dict[str, int]]
    origsr: NotRequired[SpectrogramCompressedAssetResult]


class SpectrogramAssets(TypedDict, total=False):
    duration: float
    freq_min: int
    freq_max: int
    noise_filter_threshold: float
    normal: SpectrogramAssetResult
    compressed: SpectrogramCompressedAssetResult
    metadata_origsr: NotRequired[dict[str, Any]]


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
    widths: list[float] | None = None,
) -> SpectrogramAssetResult | None:
    result: SpectrogramAssetResult = {}
    if paths:
        result["paths"] = paths
    if waveplot_paths:
        result["waveplots"] = waveplot_paths
    if size is not None:
        result["width"] = size.width_px
        result["height"] = size.height_px
    if widths:
        result["widths"] = widths
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
    if path_overrides.get("waveplots"):
        result["waveplots"] = path_overrides["waveplots"]
    if size.compressed_origsr is not None:
        result["width"] = size.compressed_origsr.width_px
        result["height"] = size.compressed_origsr.height_px
        if size.compressed_origsr.width_px != size.compressed.width_px:
            compressed_metadata = convert_to_compressed_spectrogram_data(
                metadata,
                compressed_width=size.compressed_origsr.width_px,
            )
            result["widths"] = compressed_metadata.widths
            result["starts"] = compressed_metadata.starts
            result["stops"] = compressed_metadata.stops
    if size.mask_origsr is not None:
        result["mask_size"] = {
            "width": size.mask_origsr.width_px,
            "height": size.mask_origsr.height_px,
        }
    return result or None


def _calculate_uncompressed_widths(metadata: BatbotMetadata) -> list[float]:
    uncompressed_widths: list[float] = []
    uncompressed_width = metadata.size.uncompressed.width_px
    duration_ms = metadata.duration_ms

    if metadata.segments:
        for segment in metadata.segments:
            segment_duration = segment.end_ms - segment.start_ms
            width_px = (segment_duration / duration_ms) * uncompressed_width
            uncompressed_widths.append(width_px)
    else:
        uncompressed_widths = [uncompressed_width]
    return uncompressed_widths


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


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def generate_spectrogram_assets(
    recording_path: str, *, output_folder: str, debug: bool = False
) -> SpectrogramAssets:
    """Generate spectrogram assets from BatBot.

    BatBot is run with ``include_original_sr=True`` so additional ``.origsr.jpg``
    images are written. Those paths are split into dedicated ``origsr`` buckets in
    the returned asset JSON. Set ``USE_ORIGINAL_SR_SPECTROGRAMS`` to promote those
    assets into the main ``normal`` and ``compressed`` buckets.
    """
    batbot.pipeline(
        recording_path,
        output_folder=output_folder,
        debug=debug,
        plot_uncompressed_amplitude=True,
        include_original_sr=True,
    )
    metadata_file = Path(recording_path).with_suffix(".metadata.json").name
    metadata_file = Path(output_folder) / metadata_file
    metadata = parse_batbot_metadata(metadata_file)

    def _normalize_paths(paths: list[str]) -> list[str]:
        return [f"./{Path(p).name}" for p in paths]

    uncompressed_paths, uncompressed_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.uncompressed_path
    )
    compressed_paths, compressed_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.compressed_path
    )
    mask_paths, mask_origsr_paths = _split_origsr_paths(metadata.spectrogram.mask_path)
    waveplot_paths, waveplot_origsr_paths = _split_origsr_paths(metadata.spectrogram.waveplot_path)
    compressed_waveplot_paths, compressed_waveplot_origsr_paths = _split_origsr_paths(
        metadata.spectrogram.waveplot_compressed_path
    )

    uncompressed_paths = _normalize_paths(uncompressed_paths)
    compressed_paths = _normalize_paths(compressed_paths)
    mask_paths = _normalize_paths(mask_paths)
    waveplot_paths = _normalize_paths(waveplot_paths)
    compressed_waveplot_paths = _normalize_paths(compressed_waveplot_paths)
    uncompressed_origsr_paths = _normalize_paths(uncompressed_origsr_paths)
    compressed_origsr_paths = _normalize_paths(compressed_origsr_paths)
    mask_origsr_paths = _normalize_paths(mask_origsr_paths)
    waveplot_origsr_paths = _normalize_paths(waveplot_origsr_paths)
    compressed_waveplot_origsr_paths = _normalize_paths(compressed_waveplot_origsr_paths)

    compressed_metadata = convert_to_compressed_spectrogram_data(metadata)
    uncompressed_widths = _calculate_uncompressed_widths(metadata)
    noise_threshold_percent = round((metadata.global_threshold_amp / 255.0) * 100.0, 2)

    result: SpectrogramAssets = {
        "duration": metadata.duration_ms,
        "freq_min": metadata.frequencies.min_hz,
        "freq_max": metadata.frequencies.max_hz,
        "noise_filter_threshold": noise_threshold_percent,
        "normal": {
            "paths": uncompressed_paths,
            "waveplots": waveplot_paths,
            "width": metadata.size.uncompressed.width_px,
            "height": metadata.size.uncompressed.height_px,
            "widths": uncompressed_widths,
        },
        "compressed": {
            "paths": compressed_paths,
            "masks": mask_paths,
            "waveplots": compressed_waveplot_paths,
            "width": metadata.size.compressed.width_px,
            "height": metadata.size.compressed.height_px,
            "widths": compressed_metadata.widths,
            "starts": compressed_metadata.starts,
            "stops": compressed_metadata.stops,
        },
    }

    normal_origsr = _build_normal_origsr_asset_result(
        paths=uncompressed_origsr_paths,
        waveplot_paths=waveplot_origsr_paths,
        size=metadata.size.uncompressed_origsr,
        widths=uncompressed_widths if uncompressed_origsr_paths else None,
    )
    if normal_origsr:
        result["normal"]["origsr"] = normal_origsr

    compressed_origsr = _build_compressed_origsr_asset_result(
        metadata=metadata,
        path_overrides={
            "paths": compressed_origsr_paths,
            "masks": mask_origsr_paths,
            "waveplots": compressed_waveplot_origsr_paths,
        },
        size=metadata.size,
    )
    if compressed_origsr:
        result["compressed"]["origsr"] = compressed_origsr

    original_sr_metadata = _build_original_sr_metadata_result(metadata.metadata_origsr)
    if original_sr_metadata is not None:
        result["metadata_origsr"] = original_sr_metadata

    if USE_ORIGINAL_SR_SPECTROGRAMS:
        _promote_original_sr_assets(result)

    return result


def pipeline_filepath_validator(ctx, param, value):
    if not exists(value):
        log.error(f"Input filepath does not exist: {value}")
        ctx.exit()
    return value


@click.command("pipeline")
@click.argument(
    "filepath",
    nargs=1,
    type=str,
    callback=pipeline_filepath_validator,
)
@click.option(
    "--config",
    help="Which ML model to use for inference",
    default=None,
    type=click.Choice(["usgs"]),
)
@click.option(
    "--output",
    "output_path",
    help="Path to output folder",
    default="./output",
    type=str,
)
@click.option(
    "-d",
    "--debug/",
    is_flag=True,
    default=False,
    help="Enable debug mode with more verbose logging",
)
def pipeline(filepath, config, output_path, debug):
    """
    Run the BatBot pipeline on an input WAV filepath.

    An example output of the JSON can be seen below.

    .. code-block:: javascript

            {
                '/path/to/file.wav': {
                    'classifier': 0.5,
                }
            }
    """
    if config is not None:
        config = config.strip().lower()
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    results = generate_spectrogram_assets(filepath, output_folder=str(output_path), debug=debug)
    with open(Path(output_path) / "spectrogram_assets.json", "w") as f:
        json.dump(results, f, indent=4)


@click.command("metadata")
@click.argument(
    "metadata_filepath",
    nargs=1,
    type=str,
    callback=pipeline_filepath_validator,
)
def metadata(metadata_filepath):
    """Parse and display BatBot metadata JSON file."""
    metadata_obj = parse_batbot_metadata(metadata_filepath)
    click.echo(f"{len(metadata_obj.segments)} segments found.")
    convert_to_spectrogram_data(metadata_obj)
    compressed_data = convert_to_compressed_spectrogram_data(metadata_obj)

    with open(Path(metadata_filepath).with_suffix(".compressed_spectrogram_data.json"), "w") as f:
        json.dump(compressed_data.model_dump(), f, indent=4)


@click.group()
def cli():
    """Batbot CLI."""


cli.add_command(pipeline)
cli.add_command(metadata)


if __name__ == "__main__":
    cli()
