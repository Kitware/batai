# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "batbot",
#     "click",
#     "pydantic",
# ]
#
# [tool.uv.sources]
# batbot = { git = "https://github.com/Kitware/batbot" }
# ///
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from os.path import exists
from pathlib import Path
from typing import Any, TypedDict

import batbot
from batbot import log
import click
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpectrogramMetadata(BaseModel):
    """Metadata about the spectrogram."""

    uncompressed_path: list[str] = Field(alias="uncompressed.path")
    compressed_path: list[str] = Field(alias="compressed.path")
    mask_path: list[str] = Field(alias="mask.path")


class UncompressedSize(BaseModel):
    """Uncompressed spectrogram dimensions."""

    width_px: int = Field(alias="width.px")
    height_px: int = Field(alias="height.px")


class CompressedSize(BaseModel):
    """Compressed spectrogram dimensions."""

    width_px: int = Field(alias="width.px")
    height_px: int = Field(alias="height.px")


class SizeMetadata(BaseModel):
    """Size metadata for spectrograms."""

    uncompressed: UncompressedSize
    compressed: CompressedSize


class FrequencyMetadata(BaseModel):
    """Frequency range metadata."""

    min_hz: int = Field(alias="min.hz")
    max_hz: int = Field(alias="max.hz")
    pixels_hz: list[int] = Field(alias="pixels.hz")


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
    slope_mid_box_khz_per_ms: float | None = Field(None, alias="slope/mid[box].khz/ms")
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
        duration=round(metadata.duration_ms),
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
    starts_ms: list[float] = []
    stops_ms: list[float] = []
    widths_px_compressed: list[float] = []
    segment_times: list[float] = []
    compressed_width = metadata.size.compressed.width_px
    total_time = 0.0

    # If we have segments, use them to determine which parts are kept
    if metadata.segments:
        for segment in metadata.segments:
            starts_ms.append(segment.start_ms)
            stops_ms.append(segment.end_ms)
            time = round(segment.end_ms) - round(segment.start_ms)
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
    widths: list[float]


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
    noise_filter_threshold: float
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


def generate_spectrogram_assets(
    recording_path: str, output_folder: str, debug: bool = False
) -> SpectrogramAssets:
    batbot.pipeline(recording_path, output_folder=output_folder, debug=debug)
    # There should be a .metadata.json file in the output_base directory by replacing extentions
    metadata_file = Path(recording_path).with_suffix(".metadata.json").name
    metadata_file = Path(output_folder) / metadata_file
    metadata = parse_batbot_metadata(metadata_file)

    # from the metadata we should have the images that are used
    # Normalize paths so that they are relative to the spectrogram_assets.json
    # location (i.e., "./<filename>"), avoiding duplicated "sample" directory
    # segments when other tools join them with the assets file directory.
    def _normalize_paths(paths: list[str]) -> list[str]:
        return [f"./{Path(p).name}" for p in paths]

    uncompressed_paths = _normalize_paths(metadata.spectrogram.uncompressed_path)
    compressed_paths = _normalize_paths(metadata.spectrogram.compressed_path)
    mask_paths = _normalize_paths(metadata.spectrogram.mask_path)

    compressed_metadata = convert_to_compressed_spectrogram_data(metadata)

    # Calculate widths for uncompressed spectrogram based on segments
    uncompressed_widths: list[float] = []
    uncompressed_width = metadata.size.uncompressed.width_px
    duration_ms = metadata.duration_ms

    if metadata.segments:
        # Calculate width per segment in uncompressed space based on time duration
        for segment in metadata.segments:
            segment_duration = segment.end_ms - segment.start_ms
            width_px = (segment_duration / duration_ms) * uncompressed_width
            uncompressed_widths.append(width_px)
    else:
        # No segments - entire image is one segment
        uncompressed_widths = [uncompressed_width]

    # Convert global threshold amplitude (0–255 for 8‑bit images) to a
    # percentage in the range 0–100 for downstream consumers.
    noise_threshold_percent = round((metadata.global_threshold_amp / 255.0) * 100.0, 2)

    return {
        "duration": metadata.duration_ms,
        "freq_min": metadata.frequencies.min_hz,
        "freq_max": metadata.frequencies.max_hz,
        "noise_filter_threshold": noise_threshold_percent,
        "normal": {
            "paths": uncompressed_paths,
            "width": metadata.size.uncompressed.width_px,
            "height": metadata.size.uncompressed.height_px,
            "widths": uncompressed_widths,
        },
        "compressed": {
            "paths": compressed_paths,
            "masks": mask_paths,
            "width": metadata.size.compressed.width_px,
            "height": metadata.size.compressed.height_px,
            "widths": compressed_metadata.widths,
            "starts": compressed_metadata.starts,
            "stops": compressed_metadata.stops,
        },
    }


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
    help="Path to output Folder",
    default=None,
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
    # classifier_thresh /= 100.0

    results = generate_spectrogram_assets(filepath, output_folder=output_path, debug=debug)
    # save the assets to a json file
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
    metadata = parse_batbot_metadata(metadata_filepath)
    print(len(metadata.segments), "segments found.")
    convert_to_spectrogram_data(metadata)
    compressed_data = convert_to_compressed_spectrogram_data(metadata)

    # dump spectrogram assets

    # dump compressed spectrogram assets
    with open(Path(metadata_filepath).with_suffix(".compressed_spectrogram_data.json"), "w") as f:
        json.dump(compressed_data.model_dump(), f, indent=4)


@click.group()
def cli():
    """Batbot CLI."""


cli.add_command(pipeline)
cli.add_command(metadata)


if __name__ == "__main__":
    cli()
