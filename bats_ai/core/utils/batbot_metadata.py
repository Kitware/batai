"""Utilities for parsing and converting BatBot metadata JSON files."""

from typing import Any
import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class SpectrogramMetadata(BaseModel):
    """Metadata about the spectrogram."""
    uncompressed_path: list[str] = Field(alias="uncompressed.path")
    compressed_path: list[str] = Field(alias="compressed.path")


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
    compressed: list[CompressedSize]


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
    start_ms: float = Field(alias="start.ms")
    end_ms: float = Field(alias="end.ms")
    duration_ms: float = Field(alias="duration.ms")
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
    wav_path: str = Field(alias="wav.path")
    spectrogram: SpectrogramMetadata
    global_threshold_amp: int = Field(alias="global_threshold.amp")
    sr_hz: int = Field(alias="sr.hz")
    duration_ms: float = Field(alias="duration.ms")
    frequencies: FrequencyMetadata
    size: SizeMetadata
    segments: list[Segment]

    class Config:
        populate_by_name = True


class SpectrogramData(BaseModel):
    """Data structure for creating a Spectrogram model."""
    width: int
    height: int
    duration: int  # milliseconds
    frequency_min: int  # hz
    frequency_max: int  # hz


class CompressedSpectrogramData(BaseModel):
    """Data structure for creating a CompressedSpectrogram model."""
    length: int
    starts: list[list[int]]  # 2D array: one list per compressed image
    stops: list[list[int]]  # 2D array: one list per compressed image
    widths: list[list[int]]  # 2D array: one list per compressed image


def parse_batbot_metadata(file_path: str | Path) -> BatbotMetadata:
    """Parse a BatBot metadata JSON file.
    
    Args:
        file_path: Path to the metadata JSON file
        
    Returns:
        Parsed BatbotMetadata object
    """
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
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


def convert_to_compressed_spectrogram_data(
    metadata: BatbotMetadata
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
    uncompressed_width = metadata.size.uncompressed.width_px
    duration_ms = metadata.duration_ms
    
    # Process each compressed image
    all_starts: list[list[int]] = []
    all_stops: list[list[int]] = []
    all_widths: list[list[int]] = []
    
    for compressed_size in metadata.size.compressed:
        compressed_width = compressed_size.width_px
        
        # Convert segment times to milliseconds (starts/stops are in milliseconds)
        starts_ms: list[int] = []
        stops_ms: list[int] = []
        
        # If we have segments, use them to determine which parts are kept
        if metadata.segments:
            # Calculate which time ranges correspond to segments
            segment_ranges: list[tuple[float, float]] = []
            
            for segment in metadata.segments:
                start_ms_val = segment.start_ms
                stop_ms_val = segment.end_ms
                
                # Clamp to valid range
                start_ms_val = max(0.0, min(start_ms_val, duration_ms))
                stop_ms_val = max(0.0, min(stop_ms_val, duration_ms))
                
                if stop_ms_val > start_ms_val:
                    segment_ranges.append((start_ms_val, stop_ms_val))
            
            # Merge overlapping segments
            if segment_ranges:
                # Sort by start time
                sorted_segments = sorted(segment_ranges)
                merged: list[tuple[float, float]] = []
                
                for start, stop in sorted_segments:
                    if not merged:
                        merged.append((start, stop))
                    else:
                        last_start, last_stop = merged[-1]
                        if start <= last_stop:
                            # Merge with previous
                            merged[-1] = (last_start, max(last_stop, stop))
                        else:
                            # New segment
                            merged.append((start, stop))
                
                # Extract starts and stops (in milliseconds, rounded to integers)
                for start_ms_val, stop_ms_val in merged:
                    starts_ms.append(int(round(start_ms_val)))
                    stops_ms.append(int(round(stop_ms_val)))
        else:
            # No segments - the entire image is compressed
            starts_ms = [0]
            stops_ms = [int(round(duration_ms))]
        
        # Calculate widths in compressed space
        # The compressed image is a concatenation of the segments
        # We need to determine how wide each segment is in the compressed image
        widths_px_compressed: list[int] = []
        
        if starts_ms and stops_ms:
            # Calculate total time covered by segments
            total_time_ms = sum(
                stop - start for start, stop in zip(starts_ms, stops_ms)
            )
            
            if total_time_ms > 0:
                # Calculate compression ratio for segments
                # The compressed image width represents the total width of all segments
                # Each segment's width is proportional to its time duration
                for start_ms_val, stop_ms_val in zip(starts_ms, stops_ms):
                    segment_time_ms = stop_ms_val - start_ms_val
                    segment_width_compressed = int(round(
                        compressed_width * (segment_time_ms / total_time_ms)
                    ))
                    widths_px_compressed.append(max(1, segment_width_compressed))
            else:
                # Fallback: divide compressed width equally among segments
                if len(starts_ms) > 0:
                    width_per_segment = compressed_width // len(starts_ms)
                    widths_px_compressed = [width_per_segment] * len(starts_ms)
        else:
            # No segments - entire compressed image is one segment
            widths_px_compressed = [compressed_width]
        
        all_starts.append(starts_ms)
        all_stops.append(stops_ms)
        all_widths.append(widths_px_compressed)
    
    # If no compressed images, return empty structure
    if not all_starts:
        return CompressedSpectrogramData(
            length=0,
            starts=[],
            stops=[],
            widths=[],
        )
    
    # Calculate total length (sum of all widths in compressed space)
    total_length = sum(sum(widths) for widths in all_widths)
    
    return CompressedSpectrogramData(
        length=total_length,
        starts=all_starts,
        stops=all_stops,
        widths=all_widths,
    )
